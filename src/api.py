"""Web server: chat API for the Sabi widget, the widget files and the demo pages (FR-20, FR-21).

Start:   uv run uvicorn src.api:app --reload
Open:    http://localhost:8000/demo

Privacy: the server keeps only the travel wishes per anonymous session id, in memory,
for at most SESSION_TTL seconds. Message texts are never stored or logged.
"""

from __future__ import annotations

import time
import uuid
from functools import lru_cache
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import config
from src.data_loader import load_tours
from src.dialogue import Conversation, ConversationState
from src.illustrations import destination_svg

SESSION_TTL = 60 * 60          # 1 hour
MAX_SESSIONS = 5000
MAX_MESSAGE_LENGTH = 500
ILLUSTRATION_STYLE = {"Stad & omgeving": "Stad", "Binnenland & natuur": "Natuur", "Rondreis": "Natuur"}

app = FastAPI(title="Orange Travel – Sabi", version="2.0.0", docs_url="/api/docs", redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])


@app.middleware("http")
async def private_network_access(request: Request, call_next):
    """Allow the bookmarklet demo (a public https page calling http://localhost) in Chromium browsers."""
    response = await call_next(request)
    if request.headers.get("access-control-request-private-network") == "true":
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    message: str | None = Field(default=None, max_length=MAX_MESSAGE_LENGTH)
    payload: str | None = Field(default=None, max_length=120)
    event: str | None = Field(default=None, max_length=20)
    redacted: list[str] = Field(default_factory=list, max_length=10)   # personal data the widget already removed


class SessionStore:
    """In-memory sessions: id -> (last used, ConversationState). Nothing is written to disk."""

    def __init__(self):
        self._sessions: dict[str, tuple[float, ConversationState]] = {}
        self._lock = Lock()

    def get(self, session_id: str | None) -> tuple[str, ConversationState, bool]:
        now = time.time()
        with self._lock:
            self._sessions = {k: v for k, v in self._sessions.items() if now - v[0] < SESSION_TTL}
            if session_id and session_id in self._sessions:
                state = self._sessions[session_id][1]
                self._sessions[session_id] = (now, state)
                return session_id, state, False
            if len(self._sessions) >= MAX_SESSIONS:
                oldest = min(self._sessions, key=lambda k: self._sessions[k][0])
                del self._sessions[oldest]
            new_id = uuid.uuid4().hex
            state = ConversationState()
            self._sessions[new_id] = (now, state)
            return new_id, state, True


@lru_cache(maxsize=1)
def conversation() -> Conversation:
    return Conversation(load_tours())


sessions = SessionStore()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "tours": len(conversation().tours)}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    session_id, state, is_new = sessions.get(request.session_id)
    bot = conversation()
    if request.event == "open" or (is_new and not request.message and not request.payload):
        reply = bot.open(state)
    elif request.payload:
        reply = bot.handle(state, payload=request.payload)
    else:
        found = [kind[:40] for kind in request.redacted]
        reply = bot.handle(state, text=(request.message or "")[:MAX_MESSAGE_LENGTH], already_removed=found)
    return {"session_id": session_id, **reply.to_dict()}


@app.get("/api/tours")
def tours() -> list[dict]:
    df = conversation().tours
    columns = [config.COL_ID, config.COL_NAME, config.COL_TYPE, config.COL_PRICE, config.COL_DURATION_TEXT,
               config.COL_REGION, config.COL_DESCRIPTION, config.COL_URL]
    return df[columns].to_dict(orient="records")


@app.get("/api/illustration/{tour_id}.svg")
def illustration(tour_id: str) -> Response:
    df = conversation().tours
    match = df[df[config.COL_ID] == tour_id]
    if match.empty:
        raise HTTPException(404, "Onbekende tour")
    for ext in ("jpg", "jpeg", "png", "webp"):
        photo = config.TOUR_IMAGES_DIR / f"{tour_id}.{ext}"
        if photo.exists():
            return FileResponse(photo)
    style = ILLUSTRATION_STYLE[match.iloc[0][config.COL_TYPE]]
    svg = destination_svg(f"{tour_id}-{style}", style)
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse("/demo")


@app.get("/demo", response_class=HTMLResponse)
def demo() -> FileResponse:
    return FileResponse(config.DEMO_DIR / "index.html")


@app.get("/demo/bladwijzer", response_class=HTMLResponse)
def bookmarklet() -> FileResponse:
    return FileResponse(config.DEMO_DIR / "bladwijzer.html")


app.mount("/widget", StaticFiles(directory=config.WIDGET_DIR), name="widget")
app.mount("/assets", StaticFiles(directory=config.ASSETS_DIR), name="assets")
