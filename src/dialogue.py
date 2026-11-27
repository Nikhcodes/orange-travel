"""Conversation manager: turns one customer message into Sabi's reply.

Order of handling for every message:
    1. privacy filter: remove personal data and warn (FR-19, NFR-07)
    2. buttons (payloads) are handled directly; typed text goes through the NLU
       (intent model + slot extraction)
    3. the intent decides what Sabi does; travel wishes found in any message update
       the stored wishes (FR-04)
    4. missing wishes are asked one at a time (FR-03, NFR-08); when all four are known
       the KNN engine gives the advice (FR-07..FR-12)

The state holds only travel wishes and the ids of shown tours - never message text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from src import config, texts
from src.knowledge import KnowledgeBase
from src.nlu.privacy import check_privacy
from src.nlu.understanding import Understander
from src.recommendation_engine import Recommendation, RecommendationEngine, RecommendationResult, validate_preferences

SLOT_ORDER = ["type", "companion", "travelers", "days", "budget"]
BUDGET_CHOICES = {"Stad & omgeving": [50, 100, 200], "Binnenland & natuur": [150, 400, 800, 1500],
                  "Rondreis": [1000, 1500, 2200]}
OUT_OF_SCOPE_KB_SCORE = 0.3   # an off-topic message must match a knowledge entry well to be answered
ORDINALS = {"eerste": 1, "1": 1, "één": 1, "tweede": 2, "2": 2, "derde": 3, "3": 3, "laatste": 3}


@dataclass
class ConversationState:
    slots: dict = field(default_factory=lambda: {"type": None, "companion": None, "travelers": None, "days": None,
                                                 "budget": None, "budget_is_total": False})
    shown: list[str] = field(default_factory=list)          # tour ids of the current advice
    seen: list[str] = field(default_factory=list)           # all tour ids shown so far
    greeted: bool = False
    awaiting: str | None = None


@dataclass
class Reply:
    messages: list[dict] = field(default_factory=list)
    quick_replies: list[dict] = field(default_factory=list)
    mood: str = "neutral"

    def text(self, text: str, tone: str = "normal") -> "Reply":
        self.messages.append({"type": "text", "text": text, "tone": tone})
        return self

    def links(self, links: list[tuple[str, str]]) -> "Reply":
        self.messages.append({"type": "links", "links": [{"label": l, "url": u} for l, u in links]})
        return self

    def to_dict(self) -> dict:
        return {"messages": self.messages, "quick_replies": self.quick_replies, "mood": self.mood}


def qr(label: str, payload: str) -> dict:
    return {"label": label, "payload": payload}


class Conversation:
    """Stateless service: all state lives in ConversationState objects (one per session)."""

    def __init__(self, tours: pd.DataFrame, engine: RecommendationEngine | None = None,
                 understander: Understander | None = None, knowledge: KnowledgeBase | None = None,
                 image_url=lambda tour_id: f"/api/illustration/{tour_id}.svg"):
        self.tours = tours.reset_index(drop=True)
        self.engine = engine or RecommendationEngine(self.tours)
        self.understander = understander or Understander()
        self.knowledge = knowledge or KnowledgeBase(self.tours)
        self.image_url = image_url

    # ================================================================ public
    def open(self, state: ConversationState) -> Reply:
        reply = Reply(mood="wave")
        reply.text(texts.GREETING)
        state.greeted = True
        self._ask_next(state, reply)
        return reply

    def handle(self, state: ConversationState, text: str = "", payload: str = "",
               already_removed: list[str] | None = None) -> Reply:
        reply = Reply()
        if payload:
            return self._handle_payload(state, payload, reply)

        privacy = check_privacy(text or "")
        for kind in already_removed or []:          # removed in the browser before sending
            if kind not in privacy.found:
                privacy.found.append(kind)
        if privacy.has_personal_data:
            reply.mood = "alert"
            reply.text(texts.PRIVACY_WARNING.format(found=", ".join(privacy.found)), tone="warning")
            if not re.sub(r"\[verwijderd\]|[\W_]", "", privacy.clean_text):
                self._ask_next(state, reply, quiet=True)
                return reply
        clean = privacy.clean_text.strip()
        if not clean:
            return self._not_understood(state, reply)

        nlu = self.understander.understand(clean)
        intent = nlu.intent
        if privacy.has_personal_data and not nlu.slots.any and intent not in (
                "tour_vraag", "boeken", "medewerker", "vergelijken", "waarom", "meer_opties", "twijfel_type"):
            self._ask_next(state, reply, quiet=True)
            if not reply.quick_replies and state.shown:
                reply.quick_replies = [qr("🔄 Andere opties", "intent:more"), qr("✨ Opnieuw", "intent:restart")]
            return reply
        if not nlu.understood and not nlu.slots.any:
            answer = self.knowledge.answer(clean)
            if answer.found and answer.score >= OUT_OF_SCOPE_KB_SCORE:
                return self._answer(answer, reply, state)
            return self._not_understood(state, reply)
        if intent == "opnieuw":
            return self._restart(state, reply)
        if intent == "boeken":
            return self._booking(state, reply)
        if intent == "medewerker":
            return self._human(reply)
        if intent == "voorkeur" or (nlu.slots.any and intent == "groet"):
            return self._preferences(state, nlu.slots, reply)
        if intent == "tour_vraag":
            return self._question(state, clean, reply)
        if intent == "vergelijken":
            return self._compare(state, reply)
        if intent == "waarom":
            return self._why(state, reply, self._ordinal(clean))
        if intent == "meer_opties":
            return self._more(state, clean, reply)
        if intent == "twijfel_type":
            return self._doubt(state, reply)
        if intent == "over_bot":
            reply.text(texts.ABOUT_ME)
            self._ask_next(state, reply, quiet=True)
            if not reply.quick_replies and state.shown:
                reply.quick_replies = [qr("⚖️ Vergelijk", "intent:compare"), qr("🔄 Andere opties", "intent:more")]
            return reply
        if intent == "groet":
            reply.mood = "wave"
            reply.text(texts.GREETING if not state.greeted else "Hoi! Waarmee kan ik je helpen?")
            state.greeted = True
            self._ask_next(state, reply)
            return reply
        if intent == "bedankt_doei":
            reply.mood = "wave"
            reply.text(texts.BYE)
            reply.links([("Alle tours", config.TOURS_URL), ("Contact", config.CONTACT_URL)])
            reply.quick_replies = [qr("Opnieuw zoeken", "intent:restart")]
            return reply
        if intent == "buiten_scope" or not nlu.understood:
            answer = self.knowledge.answer(clean)
            if answer.found and intent == "buiten_scope" and answer.score >= OUT_OF_SCOPE_KB_SCORE:
                return self._answer(answer, reply)
            if intent == "buiten_scope":
                reply.text(texts.OUT_OF_SCOPE)
                self._ask_next(state, reply, quiet=True)
                return reply
            return self._not_understood(state, reply)
        return self._not_understood(state, reply)

    # ============================================================== payloads
    def _handle_payload(self, state: ConversationState, payload: str, reply: Reply) -> Reply:
        kind, _, value = payload.partition(":")
        s = state.slots
        if kind == "type" and value in config.TYPES:
            s["type"] = value
        elif kind == "companion" and value in config.COMPANIONS:
            s["companion"] = value
            s["travelers"] = {"Alleen": 1, "Stel": 2}.get(value)
        elif kind == "travelers":
            s["travelers"] = max(1, min(int(float(value)), config.MAX_TRAVELERS))
        elif kind == "days":
            s["days"] = float(value)
        elif kind == "budget":
            s["budget"], s["budget_is_total"] = float(value), False
        elif kind == "why":
            return self._why(state, reply, int(value or 1))
        elif kind == "intent":
            handlers = {"why": lambda: self._why(state, reply, 1), "compare": lambda: self._compare(state, reply),
                        "more": lambda: self._more(state, "", reply), "cheaper": lambda: self._more(state, "goedkoper", reply),
                        "human": lambda: self._human(reply), "restart": lambda: self._restart(state, reply),
                        "doubt": lambda: self._doubt(state, reply), "open": lambda: self.open(state)}
            if value in handlers:
                return handlers[value]()
            return self._not_understood(state, reply)
        else:
            return self._not_understood(state, reply)
        state.shown = []
        self._ask_next(state, reply)
        return reply

    # ============================================================ wishes
    def _preferences(self, state: ConversationState, slots, reply: Reply) -> Reply:
        s, changes, had_advice = state.slots, [], bool(state.shown)
        if slots.tour_type and slots.tour_type != s["type"]:
            changes.append(f"soort reis → {slots.tour_type}")
            s["type"] = slots.tour_type
        if slots.companion and slots.companion != s["companion"]:
            changes.append(f"reisgezelschap → {texts.COMPANION_LABELS[slots.companion].lower()}")
            s["companion"] = slots.companion
            s["travelers"] = slots.travelers
        elif slots.travelers and slots.travelers != s["travelers"]:
            changes.append(f"aantal personen → {slots.travelers}")
            s["travelers"] = slots.travelers
            if s["companion"] is None and slots.travelers == 1:
                s["companion"] = "Alleen"
        if slots.days and slots.days != s["days"]:
            changes.append(f"duur → {texts.days_text(slots.days)}")
            s["days"] = slots.days
        if slots.budget and (slots.budget != s["budget"] or slots.budget_is_total != s["budget_is_total"]):
            label = f"{texts.money(slots.budget)} {'in totaal' if slots.budget_is_total else 'p.p.'}"
            changes.append(f"budget → {label}")
            s["budget"], s["budget_is_total"] = slots.budget, slots.budget_is_total
        if slots.foreign_currency:
            reply.text(texts.FOREIGN_CURRENCY, tone="info")
        if not changes:
            return self._not_understood(state, reply)
        if had_advice:
            reply.text(texts.CHANGED.format(changes=", ".join(changes)) + ("" if changes[-1].endswith(".") else "."))
        state.shown = []
        self._ask_next(state, reply)
        return reply

    def _missing(self, state: ConversationState) -> str | None:
        s = state.slots
        for slot in SLOT_ORDER:
            if slot == "travelers":
                if s["companion"] in ("Gezin", "Vrienden") and s["travelers"] is None:
                    return slot
                continue
            if s[slot] is None:
                return slot
        return None

    def _ask_next(self, state: ConversationState, reply: Reply, quiet: bool = False) -> None:
        missing = self._missing(state)
        state.awaiting = missing
        if missing is None:
            if not quiet or not state.shown:
                self._advise(state, reply)
            return
        reply.text(texts.ASK[missing])
        reply.quick_replies = self._choices(missing, state)
        if reply.mood == "neutral":
            reply.mood = "think"

    def _choices(self, slot: str, state: ConversationState) -> list[dict]:
        if slot == "type":
            return [qr(f"{texts.TYPE_EMOJI[t]} {t}", f"type:{t}") for t in config.TYPES] + [qr("🤔 Ik twijfel", "intent:doubt")]
        if slot == "companion":
            icons = {"Alleen": "🧍", "Stel": "💑", "Gezin": "👨‍👩‍👧", "Vrienden": "👯"}
            return [qr(f"{icons[c]} {texts.COMPANION_LABELS[c]}", f"companion:{c}") for c in config.COMPANIONS]
        if slot == "travelers":
            start = 3 if state.slots["companion"] == "Gezin" else 2
            return [qr(f"{n} personen", f"travelers:{n}") for n in range(start, start + 4)] + [qr("8 of meer", "travelers:8")]
        if slot == "days":
            return [qr(label, f"days:{value}") for label, value in config.DURATION_OPTIONS.items()]
        if slot == "budget":
            amounts = BUDGET_CHOICES.get(state.slots["type"], [100, 400, 1000])
            return [qr(f"{texts.money(a)} p.p.", f"budget:{a}") for a in amounts]
        return []

    def _customer(self, state: ConversationState):
        s = state.slots
        travelers = s["travelers"] or {"Alleen": 1, "Stel": 2}.get(s["companion"], 2)
        budget = s["budget"] / travelers if s["budget_is_total"] else s["budget"]
        return validate_preferences(budget, s["days"], s["type"], s["companion"], travelers)

    # ============================================================== advice
    def _advise(self, state: ConversationState, reply: Reply, result: RecommendationResult | None = None,
                intro: str | None = None) -> None:
        result = result or self.engine.recommend(self._customer(state))
        budget = texts.money(result.customer.budget)
        if result.has_results:
            recs = result.recommendations
            reply.mood = "happy"
            reply.text(intro or texts.RESULTS[len(recs)].format(best=recs[0].name))
            if not all(r.fully_matches for r in recs):
                reply.text(texts.PARTLY, tone="info")
            reply.messages.append({"type": "cards", "variant": "advice", "cards": self._cards(recs, badges=True)})
            state.shown = [r.tour_id for r in recs]
            state.seen = list(dict.fromkeys(state.seen + state.shown))
            reply.quick_replies = [qr("❓ Waarom deze?", "intent:why"), qr("⚖️ Vergelijk", "intent:compare"),
                                   qr("🔄 Andere opties", "intent:more"), qr("💸 Iets goedkopers", "intent:cheaper"),
                                   qr("👩‍💼 Spreek een adviseur", "intent:human"), qr("✨ Opnieuw", "intent:restart")]
        else:
            reply.mood = "sad"
            same_type = result.over_budget and result.over_budget[0].tour_type == result.customer.tour_type
            reply.text(texts.OVER_BUDGET.format(budget=budget, type_part=f" voor {result.customer.tour_type.lower()}"
                                                if same_type else ""), tone="warning")
            reply.messages.append({"type": "cards", "variant": "over_budget", "cards": self._cards(result.over_budget)})
            state.shown = [r.tour_id for r in result.over_budget]
            cheapest = min(r.price for r in result.over_budget)
            reply.quick_replies = [qr(f"Budget naar {texts.money(cheapest)} p.p.", f"budget:{cheapest}"),
                                   qr("Andere soort reis", "intent:doubt"), qr("👩‍💼 Spreek een adviseur", "intent:human"),
                                   qr("✨ Opnieuw", "intent:restart")]

    def _cards(self, recs: list[Recommendation], badges: bool = False) -> list[dict]:
        cheapest = min(recs, key=lambda r: (r.price, r.rank)).tour_id if len(recs) > 1 else None
        cards = []
        for r in recs:
            card_badges = []
            if badges and r.rank == 1:
                card_badges.append({"label": "Beste match", "kind": "best"})
            if badges and r.tour_id == cheapest:
                card_badges.append({"label": "Voordeligst", "kind": "cheap"})
            if not r.within_budget:
                card_badges.append({"label": f"+{texts.money(r.price - r.budget_per_person)} boven budget", "kind": "over"})
            elif not r.fully_matches:
                card_badges.append({"label": "Past deels", "kind": "partial"})
            reasons = []
            for reason in r.reasons:
                kind = "info" if reason.code == "intensity_high" else ("ok" if reason.positive else "warn")
                if reason.code in ("budget_ok", "budget_over"):
                    continue
                reasons.append({"text": texts.render_reason(reason.code, reason.params), "kind": kind})
            cards.append({
                "id": r.tour_id, "rank": r.rank, "name": r.name, "type": r.tour_type,
                "emoji": texts.TYPE_EMOJI[r.tour_type], "duration": r.duration_text, "region": r.region,
                "description": r.description, "price": texts.money(r.price),
                "total": texts.money(r.total_price) if r.travelers > 1 else None, "travelers": r.travelers,
                "remaining": texts.money(r.remaining) if r.within_budget else None,
                "min_persons": r.min_persons, "badges": card_badges, "reasons": reasons, "note": r.note,
                "url": r.url, "image": self.image_url(r.tour_id), "within_budget": r.within_budget,
            })
        return cards

    def _current(self, state: ConversationState) -> list[Recommendation]:
        if not state.shown or self._missing(state):
            return []
        result = self.engine.recommend(self._customer(state))
        pool = result.recommendations + result.over_budget
        ranked, vector = self.engine.ranking(result.customer)
        by_id = {r.tour_id: r for r in pool}
        recs = []
        for i, tour_id in enumerate(state.shown, start=1):
            if tour_id in by_id:
                rec = by_id[tour_id]
            else:
                row = ranked[ranked[config.COL_ID] == tour_id].iloc[0]
                rec = self.engine._build(i, row, result.customer, vector)
            rec.rank = i
            recs.append(rec)
        return recs

    # ===================================================== follow-ups
    def _why(self, state: ConversationState, reply: Reply, rank: int = 1) -> Reply:
        recs = self._current(state)
        if not recs:
            reply.text(texts.NO_RESULTS_TO_TALK_ABOUT)
            self._ask_next(state, reply, quiet=True)
            return reply
        rec = recs[min(max(rank, 1), len(recs)) - 1]
        reply.text(texts.WHY_INTRO.format(name=rec.name))
        lines = []
        for reason in rec.reasons:
            icon = "ℹ️" if reason.code == "intensity_high" else ("✅" if reason.positive else "⚠️")
            lines.append(f"{icon} {texts.render_reason(reason.code, reason.params)}")
        reply.text("\n".join(lines))
        if rec.rank == 1 and len(recs) > 1:
            reply.text("Van je opties lijkt deze qua duur, budget, soort reis en gezelschap samen het meest op wat je "
                       "zoekt. Bij gelijke duur weegt de soort reis zwaarder dan het gezelschap, zoals afgesproken in "
                       "onze prioriteiten.", tone="info")
        reply.links([(f"Bekijk {rec.name}", rec.url)])
        reply.quick_replies = [qr(f"Waarom optie {i}?", f"why:{i}") for i in range(1, len(recs) + 1) if i != rec.rank]
        reply.quick_replies += [qr("⚖️ Vergelijk", "intent:compare"), qr("🔄 Andere opties", "intent:more")]
        return reply

    def _compare(self, state: ConversationState, reply: Reply) -> Reply:
        recs = self._current(state)
        if len(recs) < 2:
            if recs:
                return self._why(state, reply, 1)
            reply.text(texts.NO_RESULTS_TO_TALK_ABOUT)
            self._ask_next(state, reply, quiet=True)
            return reply
        customer = self._customer(state)
        fits = lambda r: "✅" if r.fully_matches else "⚠️ deels"
        companion_col = config.COMPANION_COLUMNS[customer.companion]
        suit = {row[config.COL_ID]: int(row[companion_col]) for _, row in self.tours.iterrows()}
        rows = [
            {"label": "Prijs p.p.", "values": [texts.money(r.price) for r in recs]},
            {"label": f"Totaal ({customer.travelers} pers.)", "values": [texts.money(r.total_price) for r in recs]},
            {"label": "Duur", "values": [r.duration_text for r in recs]},
            {"label": "Soort reis", "values": [r.tour_type for r in recs]},
            {"label": f"Voor {texts.COMPANION_GROUP[customer.companion]}", "values": ["✅" if suit[r.tour_id] else "—" for r in recs]},
            {"label": "Min. personen", "values": [str(r.min_persons) for r in recs]},
            {"label": "Intensiteit", "values": [r.intensity for r in recs]},
            {"label": "Past bij je wensen", "values": [fits(r) for r in recs]},
        ]
        reply.text(texts.COMPARE_INTRO)
        reply.messages.append({"type": "compare", "headers": [r.name for r in recs], "rows": rows})
        best = recs[0]
        positives = [texts.render_reason(x.code, x.params).rstrip(".").lower() for x in best.reasons
                     if x.positive and x.code not in ("intensity_high", "budget_ok")][:2]
        reply.text(texts.COMPARE_BEST.format(name=best.name, reason=" en ".join(positives) or "de kleinste afstand tot je wensen"))
        reply.quick_replies = [qr(f"Waarom optie {i}?", f"why:{i}") for i in range(1, len(recs) + 1)]
        reply.quick_replies.append(qr("🔄 Andere opties", "intent:more"))
        return reply

    def _more(self, state: ConversationState, text: str, reply: Reply) -> Reply:
        if self._missing(state) or not state.shown:
            reply.text(texts.NO_RESULTS_TO_TALK_ABOUT)
            self._ask_next(state, reply, quiet=True)
            return reply
        low = text.lower()
        customer = self._customer(state)
        if re.search(r"langer|langere", low):
            state.slots["days"] = min(state.slots["days"] * 2, 16)
            reply.text(texts.CHANGED.format(changes=f"duur → {texts.days_text(state.slots['days'])}."))
            state.shown = []
            self._advise(state, reply)
            return reply
        if re.search(r"korter|kortere", low):
            state.slots["days"] = max(state.slots["days"] / 2, 0.5)
            reply.text(texts.CHANGED.format(changes=f"duur → {texts.days_text(state.slots['days'])}."))
            state.shown = []
            self._advise(state, reply)
            return reply
        ranked, vector = self.engine.ranking(customer)
        pool = ranked[ranked[config.COL_PRICE] <= customer.budget]
        intro = "Hier zijn andere opties binnen je budget:"
        if re.search(r"goedkop|voordelig|te duur|cheaper", low):
            shown_prices = [p for p in self.tours.loc[self.tours[config.COL_ID].isin(state.shown), config.COL_PRICE]]
            limit = min(shown_prices) if shown_prices else customer.budget
            pool = pool[pool[config.COL_PRICE] < limit]
            intro = f"Dit zijn opties die goedkoper zijn dan {texts.money(limit)} p.p.:"
        elif re.search(r"avontuur|pittig|actie", low):
            pool = pool[pool[config.COL_INTENSITY] == "hoog"]
            intro = "Dit zijn avontuurlijkere opties:"
        elif re.search(r"rustig|relax|minder lopen|makkelijk", low):
            pool = pool[pool[config.COL_INTENSITY] == "laag"]
            intro = "Dit zijn rustigere opties:"
        pool = pool[~pool[config.COL_ID].isin(state.seen if not re.search(r"goedkop|voordelig|te duur", low) else state.shown)]
        if pool.empty:
            reply.mood = "sad"
            reply.text(texts.NO_MORE_OPTIONS)
            reply.links([("Reis op maat", config.CUSTOM_TOUR_URL), ("Contact", config.CONTACT_URL)])
            reply.quick_replies = [qr("Ander budget", "intent:restart"), qr("👩‍💼 Spreek een adviseur", "intent:human")]
            return reply
        recs = [self.engine._build(i, row, customer, vector) for i, (_, row) in enumerate(pool.head(config.TOP_N).iterrows(), 1)]
        result = RecommendationResult(customer, recs, len(pool))
        self._advise(state, reply, result, intro=intro)
        return reply

    def _doubt(self, state: ConversationState, reply: Reply) -> Reply:
        reply.text(texts.DOUBT_INTRO)
        items = []
        for tour_type in config.TYPES:
            item = {"title": f"{texts.TYPE_EMOJI[tour_type]} {tour_type}", "text": texts.TYPE_EXPLAIN[tour_type]}
            if state.slots["budget"] and state.slots["companion"] and state.slots["days"]:
                trial = dict(state.slots, type=tour_type)
                example = self.engine.recommend(self._customer(ConversationState(slots=trial)))
                matches = [r for r in example.recommendations if r.tour_type == tour_type]
                if matches:
                    item["example"] = f"Bijvoorbeeld voor jou: {matches[0].name} ({texts.money(matches[0].price)} p.p.)"
            items.append(item)
        reply.messages.append({"type": "list", "items": items})
        reply.text(texts.DOUBT_OUTRO)
        reply.quick_replies = [qr(f"{texts.TYPE_EMOJI[t]} {t}", f"type:{t}") for t in config.TYPES]
        reply.mood = "think"
        return reply

    # ============================================================ info
    def _question(self, state: ConversationState, text: str, reply: Reply) -> Reply:
        answer = self.knowledge.answer(text)
        if not answer.found:
            reply.mood = "think"
            reply.text(texts.NOT_KNOWN)
            reply.links([("Contact Orange Travel", config.CONTACT_URL)])
            self._ask_next(state, reply, quiet=True)
            return reply
        return self._answer(answer, reply, state)

    def _answer(self, answer, reply: Reply, state: ConversationState | None = None) -> Reply:
        reply.text(answer.text)
        reply.links([("Bron: orangesuriname.com", answer.source_url)])
        if state is not None and self._missing(state):
            self._ask_next(state, reply, quiet=True)
        elif state is not None and state.shown:
            reply.quick_replies = [qr("⚖️ Vergelijk", "intent:compare"), qr("🔄 Andere opties", "intent:more")]
        return reply

    def _booking(self, state: ConversationState, reply: Reply) -> Reply:
        reply.text(texts.BOOKING)
        links = []
        if state.shown:
            for tour_id in state.shown[:3]:
                row = self.tours[self.tours[config.COL_ID] == tour_id].iloc[0]
                links.append((f"Boeken: {row[config.COL_NAME]}", row[config.COL_URL]))
        links += [("Contact & belafspraak", config.CONTACT_URL), ("Betalingsbeleid", config.PAYMENT_URL)]
        reply.links(links)
        reply.quick_replies = [qr("👩‍💼 Spreek een adviseur", "intent:human")]
        return reply

    def _human(self, reply: Reply) -> Reply:
        reply.mood = "wave"
        reply.text(texts.HUMAN)
        reply.links([("Contact & belafspraak", config.CONTACT_URL), ("Reis op maat", config.CUSTOM_TOUR_URL)])
        return reply

    def _restart(self, state: ConversationState, reply: Reply) -> Reply:
        state.slots = ConversationState().slots
        state.shown, state.seen = [], []
        reply.mood = "wave"
        reply.text(texts.RESTARTED)
        self._ask_next(state, reply)
        return reply

    def _not_understood(self, state: ConversationState, reply: Reply) -> Reply:
        reply.mood = "think"
        reply.text(texts.NOT_UNDERSTOOD)
        missing = self._missing(state)
        if missing:
            reply.quick_replies = self._choices(missing, state)
        else:
            reply.quick_replies = [qr("🔄 Andere opties", "intent:more"), qr("👩‍💼 Spreek een adviseur", "intent:human"),
                                   qr("✨ Opnieuw", "intent:restart")]
        return reply

    @staticmethod
    def _ordinal(text: str) -> int:
        low = text.lower()
        for word, number in ORDINALS.items():
            if re.search(rf"\b{word}\b", low):
                return number
        return 1
