"""The client chatbot: one page, a short conversation with Lora, then the advice.

Conversation state lives in st.session_state["ot"]:
    messages   list of {"role": "bot"|"user", "key": text key, "params": raw values}
               Texts are rendered at display time, so switching language
               translates the whole conversation.
    slots      the answers: category, companion, travelers, days, budget, budget_is_total
    new_index  index of the bot message that should play the typing animation once
"""

import re
from html import escape

import streamlit as st

from src import config
from src.i18n import (CATEGORY_LABELS, CATEGORY_TAGLINES, COMPANION_LABELS, COMPANION_SHORT, format_usd,
                      render_reason, t)
from src.recommendation_engine import (InvalidPreferencesError, Recommendation, RecommendationEngine,
                                       RecommendationResult, validate_preferences)
from src.text_parser import parse_wish
from src.ui import media
from src.ui.theme import CLOUD, HERO_ROUTE, HERO_SCENE

COMPANION_ICONS = {"Alleen": ":material/person:", "Stel": ":material/favorite:",
                   "Gezin": ":material/family_restroom:", "Vrienden": ":material/groups:"}
DAY_PRESETS = [("days_weekend", 3), ("days_midweek", 5), ("days_week", 7), ("days_10", 10), ("days_2weeks", 14)]
EMPTY_SLOTS = {"category": None, "companion": None, "travelers": None, "days": None,
               "budget": None, "budget_is_total": False}


# ------------------------------------------------------------------ state
def _state() -> dict:
    if "ot" not in st.session_state:
        st.session_state["ot"] = {
            "messages": [{"role": "bot", "key": "greet", "params": {}}],
            "slots": dict(EMPTY_SLOTS),
            "new_index": None,
            "show_other_days": False,
        }
        _ask_next(st.session_state["ot"])
    return st.session_state["ot"]


def _say(state: dict, role: str, key: str, **params) -> None:
    state["messages"].append({"role": role, "key": key, "params": params})
    if role == "bot":
        state["new_index"] = len(state["messages"]) - 1


def _next_slot(slots: dict) -> str | None:
    if slots["category"] is None:
        return "category"
    if slots["companion"] is None:
        return "companion"
    if slots["travelers"] is None:
        return "travelers"
    if slots["days"] is None:
        return "days"
    if slots["budget"] is None:
        return "budget"
    return None


def _budget_per_person(slots: dict) -> float:
    travelers = slots["travelers"] or 1
    return slots["budget"] / travelers if slots["budget_is_total"] else slots["budget"]


def _ask_next(state: dict) -> None:
    """Ask the next open question, or give the advice when everything is known."""
    slots = state["slots"]
    if slots["companion"] in ("Alleen", "Stel") and slots["travelers"] is None:
        slots["travelers"] = 1 if slots["companion"] == "Alleen" else 2
    nxt = _next_slot(slots)
    if nxt:
        _say(state, "bot", f"ask_{nxt}")
        return
    result = get_engine().recommend(_customer(slots))
    state["result"] = result
    if not result.has_results:
        cheapest = result.cheapest_in_category
        _say(state, "bot", "no_results", category=slots["category"], budget=result.customer.budget,
             cheapest=cheapest)
    elif len(result.recommendations) == config.TOP_N:
        _say(state, "bot", "results_3", n=len(result.recommendations), best=result.recommendations[0].name)
    else:
        _say(state, "bot", "results_few", n=len(result.recommendations))


def _customer(slots: dict):
    return validate_preferences(_budget_per_person(slots), int(slots["days"]), slots["category"], slots["companion"])


def _reset() -> None:
    st.session_state.pop("ot", None)


def _set(slot: str, value, user_key: str, **params) -> None:
    state = _state()
    state["slots"][slot] = value
    state.pop("result", None)
    if slot == "companion":
        state["slots"]["travelers"] = None
    _say(state, "user", user_key, **params)
    _ask_next(state)


def _set_budget(value: float, is_total: bool) -> None:
    state = _state()
    state["slots"]["budget"], state["slots"]["budget_is_total"] = float(value), is_total
    state.pop("result", None)
    travelers = state["slots"]["travelers"] or 1
    if is_total and travelers > 1:
        _say(state, "user", "u_budget_total", total=value, budget=value / travelers)
    else:
        _say(state, "user", "u_budget_pp", budget=value)
    _ask_next(state)


def _clear(*slots: str) -> None:
    state = _state()
    for slot in slots:
        state["slots"][slot] = EMPTY_SLOTS[slot]
    state.pop("result", None)
    _ask_next(state)


def _handle_text(text: str) -> None:
    state = _state()
    wish = parse_wish(text)
    if wish.restart:
        _reset()
        return
    state["messages"].append({"role": "user", "key": "raw", "params": {"text": text}})
    if wish.is_empty:
        _say(state, "bot", "not_understood")
        return
    slots = state["slots"]
    if wish.category:
        slots["category"] = wish.category
    if wish.companion:
        slots["companion"] = wish.companion
        slots["travelers"] = wish.travelers
    elif wish.travelers:
        slots["travelers"] = wish.travelers
    if wish.days:
        slots["days"] = wish.days
    if wish.budget:
        slots["budget"], slots["budget_is_total"] = wish.budget, wish.budget_is_total
    state.pop("result", None)
    _say(state, "bot", "understood", slots=dict(slots))
    _ask_next(state)


# ---------------------------------------------------------------- engine
@st.cache_resource
def get_engine() -> RecommendationEngine:
    from src.data_loader import load_destinations
    return RecommendationEngine(load_destinations())


# ------------------------------------------------------------- rendering
def _md(text: str) -> str:
    """Tiny, safe markdown: **bold** and *italic* only (input is escaped first)."""
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)


def _summary(slots: dict, lang: str) -> str:
    parts = []
    if slots.get("category"):
        parts.append(CATEGORY_LABELS[lang][slots["category"]].lower())
    if slots.get("companion"):
        parts.append(COMPANION_LABELS[lang][slots["companion"]].lower())
    if slots.get("travelers") and slots["travelers"] > 2:
        parts.append(t("u_travelers", lang, n=slots["travelers"]))
    if slots.get("days"):
        parts.append(t("u_days", lang, days=slots["days"]))
    if slots.get("budget"):
        key = "u_budget_total" if slots.get("budget_is_total") and (slots.get("travelers") or 1) > 1 else "u_budget_pp"
        travelers = slots.get("travelers") or 1
        parts.append(t(key, lang, budget=format_usd(_budget_per_person({**slots, "travelers": travelers})),
                       total=format_usd(slots["budget"])))
    return ", ".join(parts)


def _message_html(message: dict, lang: str) -> str:
    key, p = message["key"], message["params"]
    if key == "raw":
        return escape(p["text"])
    values = {}
    if "category" in p:
        values["category"] = CATEGORY_LABELS[lang][p["category"]]
        values["category_lower"] = CATEGORY_LABELS[lang][p["category"]].lower()
    if "companion" in p:
        values["companion"] = COMPANION_LABELS[lang][p["companion"]]
    for money in ("budget", "total", "price", "short"):
        if money in p:
            values[money] = format_usd(p[money])
    for plain in ("n", "days", "best"):
        if plain in p:
            values[plain] = p[plain]
    if key == "understood":
        values["summary"] = _summary(p["slots"], lang)
    if key == "results_few":
        values["trip"] = t("trip_one" if p["n"] == 1 else "trip_many", lang)
    html = _md(t(key, lang, **values))
    if key == "no_results" and p.get("cheapest"):
        c = p["cheapest"]
        html += (f'<div class="ot-info"><div class="label">{escape(t("cheapest_label", lang))}</div>'
                 + _md(t("cheapest_text", lang, category_lower=values["category_lower"], name=c["name"],
                         price=format_usd(c["price"]), short=format_usd(c["price"] - p["budget"]))) + "</div>")
    return html


def _render_messages(state: dict, lang: str) -> None:
    bird = f'<img src="{media.file_uri(media.LOVEBIRD)}" alt="">'
    rows = []
    for index, message in enumerate(state["messages"]):
        is_new = index == state.get("new_index")
        body = _message_html(message, lang)
        if message["role"] == "bot":
            bubble = f'<div class="ot-bubble">{body}</div>'
            if is_new:
                bubble = f'<div class="ot-newwrap"><div class="ot-typing"><span></span><span></span><span></span></div>{bubble}</div>'
            rows.append(f'<div class="ot-row bot{" new" if is_new else ""}"><div class="ot-avatar">{bird}</div>{bubble}</div>')
        else:
            rows.append(f'<div class="ot-row user"><div class="ot-bubble">{body}</div></div>')
    st.markdown(f'<div class="ot-chat">{"".join(rows)}</div>', unsafe_allow_html=True)
    state["new_index"] = None  # animate each bot message only once


def _render_reply(state: dict, lang: str) -> None:
    """The answer controls for the current open question."""
    slot = _next_slot(state["slots"])
    if slot is None:
        return
    with st.container(key="reply"):
        if slot == "category":
            for column, category in zip(st.columns(3, gap="small"), config.CATEGORIES):
                with column:
                    st.markdown(f'<div class="ot-tile"><img src="{media.category_image_uri(category)}" alt=""></div>',
                                unsafe_allow_html=True)
                    st.button(CATEGORY_LABELS[lang][category], key=f"cat_{category}", width="stretch",
                              on_click=_set, args=("category", category, "u_category"), kwargs={"category": category})
                    st.markdown(f'<div class="ot-tagline">{escape(CATEGORY_TAGLINES[lang][category])}</div>',
                                unsafe_allow_html=True)
        elif slot == "companion":
            for column, companion in zip(st.columns(4, gap="small"), config.COMPANIONS):
                with column:
                    st.button(COMPANION_LABELS[lang][companion], key=f"comp_{companion}", icon=COMPANION_ICONS[companion],
                              width="stretch", on_click=_set, args=("companion", companion, "u_companion"),
                              kwargs={"companion": companion})
        elif slot == "travelers":
            left, right = st.columns([2, 1], vertical_alignment="bottom")
            with left:
                n = st.number_input(t("travelers_label", lang), min_value=2, max_value=config.MAX_TRAVELERS, value=4, step=1)
            with right:
                st.button(t("next", lang), type="primary", width="stretch", on_click=_set,
                          args=("travelers", int(n), "u_travelers"), kwargs={"n": int(n)})
        elif slot == "days":
            columns = st.columns(len(DAY_PRESETS) + 1, gap="small")
            for column, (key, days) in zip(columns, DAY_PRESETS):
                with column:
                    label = t(key, lang) if key == "days_10" else f"{t(key, lang)} · {days}"
                    st.button(label, key=f"days_{days}", width="stretch", on_click=_set,
                              args=("days", days, "u_days"), kwargs={"days": days})
            with columns[-1]:
                if st.button(t("days_other", lang), key="days_other", width="stretch"):
                    state["show_other_days"] = True
            if state.get("show_other_days"):
                left, right = st.columns([2, 1], vertical_alignment="bottom")
                with left:
                    d = st.number_input(t("days_unit", lang).capitalize(), min_value=1, max_value=60, value=8, step=1)
                with right:
                    st.button(t("next", lang), type="primary", width="stretch", on_click=_set,
                              args=("days", int(d), "u_days"), kwargs={"days": int(d)})
        elif slot == "budget":
            travelers = state["slots"]["travelers"] or 1
            is_total = False
            if travelers > 1:
                mode = st.segmented_control(" ", ["pp", "total"], default="pp", label_visibility="collapsed",
                                            format_func=lambda m: t("budget_mode_pp" if m == "pp" else "budget_mode_total", lang))
                is_total = mode == "total"
            maximum = 6000 * (travelers if is_total else 1)
            default = min(1500 * (travelers if is_total else 1), maximum)
            value = st.slider(t("budget_label", lang), min_value=0, max_value=maximum, value=default,
                              step=50 if not is_total else 100, format="$%d", key=f"budget_{is_total}_{travelers}")
            if travelers > 1:
                hint = (t("budget_equals_pp", lang, pp=format_usd(value / travelers)) if is_total
                        else t("budget_equals_total", lang, total=format_usd(value * travelers), n=travelers))
                st.markdown(f'<div class="ot-budget-hint"><b>{escape(hint)}</b></div>', unsafe_allow_html=True)
            if st.button(t("search", lang), type="primary", icon=":material/travel_explore:", width="stretch"):
                if value <= 0:
                    st.error(t("err_budget_positive", lang))
                else:
                    _set_budget(value, is_total)
                    st.rerun()


def _badges(result: RecommendationResult) -> dict[int, list[str]]:
    """Which labels each recommendation gets. Based only on real data in the top 3."""
    recs = result.recommendations
    labels = {r.rank: [] for r in recs}
    if not recs:
        return labels
    labels[1].append("best")
    if len(recs) > 1:
        cheapest = min(recs, key=lambda r: (r.price, r.rank))
        labels[cheapest.rank].append("cheap")
        longest = max(recs, key=lambda r: (r.days, -r.rank))
        if longest.days > min(r.days for r in recs):
            labels[longest.rank].append("long")
    return labels


def _card(rec: Recommendation, badges: list[str], travelers: int, delay: float, lang: str, row: dict) -> str:
    badge_text = {"best": ("best", "★ " + t("badge_best", lang)), "cheap": ("cheap", "$ " + t("badge_cheapest", lang)),
                  "long": ("", "☼ " + t("badge_longest", lang))}
    badge_html = "".join(f'<span class="ot-badge {badge_text[b][0]}">{escape(badge_text[b][1])}</span>' for b in badges)
    image = media.destination_image_uri(rec.destination_id, rec.category, row.get(config.COL_IMAGE))
    reasons = [r for r in rec.reasons if r.code not in ("category_match", "within_budget")]
    why = "".join(f'<li class="{"pos" if r.positive else "neg"}">{escape(render_reason(r, lang))}</li>' for r in reasons)
    total = (f'<div class="ot-total">{escape(t("total_for", lang, total=format_usd(rec.price * travelers), n=travelers))}</div>'
             if travelers > 1 else "")
    facts = "".join(f'<span class="ot-fact">{escape(x)}</span>' for x in (
        f"{rec.days} {t('days_unit', lang)}", CATEGORY_LABELS[lang][rec.category], COMPANION_SHORT[lang][rec.companion]))
    return f"""<div class="ot-card{' best' if 'best' in badges else ''}" style="animation-delay:{delay:.2f}s">
      <div class="img"><img src="{image}" alt="{escape(rec.name)}"><div class="ot-badges">{badge_html}</div></div>
      <div class="body">
        <h3>{escape(rec.name)}</h3>
        <div class="desc">{escape(row.get(config.COL_DESCRIPTION) or "")}</div>
        <div class="ot-facts">{facts}</div>
        <div class="ot-price"><span class="amount">{format_usd(rec.price)}</span><span class="unit">{escape(t("per_person", lang))}</span></div>
        {total}
        <span class="ot-left">{escape(t("remaining", lang, amount=format_usd(rec.remaining_budget)))}</span>
        <ul class="ot-why">{why}</ul>
      </div></div>"""


def _render_results(state: dict, lang: str) -> None:
    result: RecommendationResult | None = state.get("result")
    if result is None:
        return
    slots = state["slots"]
    pills = "".join(f'<span class="ot-pill">{escape(p)}</span>' for p in _summary(slots, lang).split(", "))
    st.markdown(f'<div class="ot-summary"><span class="title">{escape(t("summary_title", lang))}</span>{pills}</div>',
                unsafe_allow_html=True)

    if result.has_results:
        rows = get_engine().destinations.set_index(config.COL_NAME)
        badges = _badges(result)
        n = len(result.recommendations)
        if n == config.TOP_N:
            columns = st.columns(n, gap="medium")
        else:  # centre one or two cards instead of leaving empty space on the right
            pad = (config.TOP_N - n) / 2
            columns = st.columns([pad] + [1] * n + [pad], gap="medium")[1:-1]
        for i, rec in enumerate(result.recommendations):
            with columns[i]:
                st.markdown(_card(rec, badges[rec.rank], slots["travelers"] or 1, 0.15 + i * 0.15, lang,
                                  rows.loc[rec.name].to_dict()), unsafe_allow_html=True)

    with st.container(key="actions"):
        buttons = [("restart", ":material/restart_alt:", _reset, ())]
        buttons.insert(0, ("change_category", ":material/explore:", _clear, ("category",)))
        buttons.insert(0, ("change_budget", ":material/payments:", _clear, ("budget",)))
        if not result.has_results and result.cheapest_in_category:
            price = result.cheapest_in_category["price"]
            buttons.insert(0, ("raise_budget", ":material/trending_up:", _set_budget, (price, False)))
        spacer, *cols, spacer2 = st.columns([0.5] + [1.4] * len(buttons) + [0.5])
        for column, (key, icon, callback, args) in zip(cols, buttons):
            with column:
                label = t(key, lang, price=format_usd(result.cheapest_in_category["price"])) if key == "raise_budget" else t(key, lang)
                st.button(label, key=f"act_{key}", icon=icon, width="stretch", on_click=callback, args=args,
                          type="primary" if key == "raise_budget" else "secondary")
    st.markdown(f'<div class="ot-disclaimer">{escape(t("disclaimer", lang))}</div>', unsafe_allow_html=True)


def render_hero(lang: str) -> None:
    clouds = (f'<div class="ot-cloud" style="top:70px;left:0">{CLOUD}</div>'
              f'<div class="ot-cloud" style="top:160px;left:-400px;animation-duration:55s">{CLOUD}</div>')
    st.markdown(f"""<div class="ot-hero">{clouds}
      <div class="birdwrap">{HERO_ROUTE}<img class="bird" src="{media.file_uri(media.LOVEBIRD)}" alt=""></div>
      <div class="copy"><span class="kicker">✈ Orange Travel Suriname</span>
        <h1>{escape(t("hero_title", lang))}</h1><p>{escape(t("hero_subtitle", lang))}</p></div>
      {HERO_SCENE}</div>""", unsafe_allow_html=True)


def client_page() -> None:
    lang = st.session_state.get("lang") or "nl"
    render_hero(lang)
    state = _state()

    _, center, _ = st.columns([0.6, 5, 0.6])
    with center:
        _render_messages(state, lang)
        _render_reply(state, lang)
    _render_results(state, lang)
    st.markdown(f'<div class="ot-disclaimer">{escape(t("notice", lang))}</div>', unsafe_allow_html=True)

    text = st.chat_input(t("chat_placeholder", lang))
    if text:
        _handle_text(text)
        st.rerun()
