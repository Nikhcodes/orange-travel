"""Conversation behaviour, one test per functional requirement where possible."""

from src.dialogue import ConversationState


def texts_of(reply):
    return " ".join(m["text"] for m in reply.messages if m["type"] == "text")


def cards_of(reply, variant="advice"):
    return [c for m in reply.messages if m["type"] == "cards" and m["variant"] == variant for c in m["cards"]]


def links_of(reply):
    return [l["url"] for m in reply.messages if m["type"] == "links" for l in m["links"]]


def full(bot, state):
    for payload in ("type:Binnenland & natuur", "companion:Stel", "days:2.5", "budget:400"):
        reply = bot.handle(state, payload=payload)
    return reply


def test_fr01_fr03_nfr08_asks_one_question_at_a_time(bot, state):
    reply = bot.open(state)
    assert "Waar heb je zin in" in texts_of(reply) and reply.quick_replies
    assert "budget" not in texts_of(reply).lower()
    reply = bot.handle(state, payload="type:Stad & omgeving")
    assert "Met wie" in texts_of(reply)


def test_fr02_buttons_and_free_text_both_work(bot):
    a, b = ConversationState(), ConversationState()
    by_buttons = full(bot, a)
    by_text = bot.handle(b, text="binnenland, 2-3 dagen, met mijn vriendin, 400 euro p.p.")
    by_text = bot.handle(b, text="2 tot 3 dagen") if not cards_of(by_text) else by_text
    assert cards_of(by_buttons) and (cards_of(by_text) or "Hoeveel tijd" in texts_of(by_text))


def test_fr04_change_a_wish_with_a_new_message(bot, state):
    full(bot, state)
    reply = bot.handle(state, text="toch liever 1 dag")
    assert "aangepast" in texts_of(reply) and state.slots["days"] == 1
    assert cards_of(reply)


def test_fr05_doubt_between_types(bot, state):
    reply = bot.handle(state, text="ik twijfel tussen stad en binnenland")
    assert any(m["type"] == "list" and len(m["items"]) == 3 for m in reply.messages)


def test_fr06_follow_up_questions(bot, state):
    full(bot, state)
    assert "Daarom raad ik" in texts_of(bot.handle(state, text="waarom de tweede?"))
    cheaper = bot.handle(state, text="heb je iets goedkopers")
    assert all(float(c["price"].strip("€").replace(".", "").replace(",", ".")) < 400 for c in cards_of(cheaper))


def test_fr09_fr10_cards_and_comparison(bot, state):
    reply = full(bot, state)
    card = cards_of(reply)[0]
    assert card["price"] and card["duration"] and card["reasons"] and card["url"]
    compare = bot.handle(state, payload="intent:compare")
    assert any(m["type"] == "compare" for m in compare.messages) and "past het beste" in texts_of(compare)


def test_fr12_over_budget_options_are_clearly_marked(bot, state):
    for payload in ("type:Binnenland & natuur", "companion:Gezin", "travelers:4", "days:1", "budget:15"):
        reply = bot.handle(state, payload=payload)
    assert "boven je budget" in texts_of(reply).lower()
    over = cards_of(reply, "over_budget")
    assert over and all(not c["within_budget"] and any(b["kind"] == "over" for b in c["badges"]) for c in over)
    assert not cards_of(reply, "advice")


def test_fr13_fr14_answers_with_source_link(bot, state):
    reply = bot.handle(state, text="hoeveel kost awarradam?")
    assert "€400" in texts_of(reply)
    assert any(u.startswith("https://www.orangesuriname.com/") for u in links_of(reply))


def test_fr15_says_when_it_does_not_understand(bot, state):
    assert "begrijp ik niet" in texts_of(bot.handle(state, text="qwxzpl vbnmk"))


def test_fr16_refers_to_an_advisor(bot, state):
    reply = bot.handle(state, text="ik wil met een medewerker praten")
    assert "+597" in texts_of(reply) and any("contact" in u for u in links_of(reply))


def test_fr17_fr18_cannot_book_but_gives_links(bot, state):
    full(bot, state)
    reply = bot.handle(state, text="boek de eerste tour voor mij")
    assert "kan ik niet" in texts_of(reply)
    assert any("/tours/" in u or "/tour/" in u for u in links_of(reply))


def test_fr19_nfr07_personal_data_warning_and_not_used(bot, state):
    reply = bot.handle(state, text="mijn email is jan@test.sr")
    assert "persoonsgegevens" in texts_of(reply) and reply.mood == "alert"
    assert "jan@test.sr" not in str(state.__dict__)


def test_pc02_stays_on_topic(bot, state):
    assert "alleen met tours" in texts_of(bot.handle(state, text="vertel een grap"))
