"""Web interface (FR-20, FR-21): chat API, widget files and demo pages."""

from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_open_and_chat_flow():
    first = client.post("/api/chat", json={"event": "open"}).json()
    sid = first["session_id"]
    assert first["messages"] and first["quick_replies"]
    reply = client.post("/api/chat", json={"session_id": sid, "payload": "type:Stad & omgeving"}).json()
    assert reply["session_id"] == sid and "Met wie" in reply["messages"][-1]["text"]


def test_message_length_is_limited():
    assert client.post("/api/chat", json={"message": "x" * 600}).status_code == 422


def test_widget_demo_and_illustrations_are_served():
    assert "OrangeSabi" in client.get("/widget/sabi.js").text
    assert client.get("/widget/sabi.css").status_code == 200
    assert "sabi.js" in client.get("/demo").text
    assert client.get("/api/illustration/T01.svg").headers["content-type"].startswith("image/svg")
    assert client.get("/api/illustration/NOPE.svg").status_code == 404
    assert len(client.get("/api/tours").json()) == 42


def test_cors_and_private_network_preflight():
    r = client.options("/api/chat", headers={"Origin": "https://www.orangesuriname.com", "Access-Control-Request-Method": "POST",
                                             "Access-Control-Request-Private-Network": "true"})
    assert r.headers.get("access-control-allow-origin") in ("*", "https://www.orangesuriname.com")
    assert r.headers.get("access-control-allow-private-network") == "true"


def test_fr19_personal_data_removed_in_browser_is_still_warned_about():
    reply = client.post("/api/chat", json={"message": "mijn email is [verwijderd]", "redacted": ["e-mailadres"]}).json()
    assert "persoonsgegevens" in " ".join(m.get("text", "") for m in reply["messages"])
