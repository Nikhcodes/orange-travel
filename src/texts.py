"""All sentences Sabi says (Dutch). Tone: welcoming, friendly and professional (NFR-05).

Kept in one place so the group can adjust the wording without touching the logic.
"""

from src import config

BOT_NAME = "Sabi"

TYPE_LABELS = {
    "Stad & omgeving": "Stad & omgeving",
    "Binnenland & natuur": "Binnenland & natuur",
    "Rondreis": "Rondreis",
}
TYPE_EMOJI = {"Stad & omgeving": "🏙️", "Binnenland & natuur": "🌿", "Rondreis": "🗺️"}
TYPE_EXPLAIN = {
    "Stad & omgeving": "Paramaribo en de buurt: plantages in Commewijne, Peperpot, dolfijnen en de rivier. "
                       "Vaak een dagdeel of een dag, geen lange reistijd en meestal vanaf €30–€175 p.p.",
    "Binnenland & natuur": "Het regenwoud in: watervallen, het stuwmeer, Marrondorpen en jungle-lodges. "
                           "Van een dagtrip tot expedities van een week; vaak een stevigere reis.",
    "Rondreis": "Meerdere gebieden in één reis van 9 tot 16 dagen, met vervoer en overnachtingen geregeld. "
                "Ideaal als je Suriname voor het eerst ontdekt; vanaf ± €845 p.p.",
}
COMPANION_LABELS = {"Alleen": "Alleen", "Stel": "Met z'n tweeën", "Gezin": "Met het gezin", "Vrienden": "Met vrienden"}
COMPANION_GROUP = {"Alleen": "solo-reizigers", "Stel": "stellen", "Gezin": "gezinnen", "Vrienden": "vriendengroepen"}

GREETING = (f"Hoi! Ik ben **{BOT_NAME}**, de reisadviseur van Orange Travel 🧡 "
            "Ik help je in een paar korte vragen aan een passende tour in Suriname.")
ABOUT_ME = (f"Ik ben **{BOT_NAME}**, een rotshaan uit het Surinaamse regenwoud 🐦 "
            "*Sabi* betekent in het Sranantongo *weten*, en dat probeer ik ook te zijn: een slimme, behulpzame "
            "adviseur. Ik zoek tours van Orange Travel die passen bij je budget, tijd en wensen, en ik beantwoord "
            "vragen met informatie van de website van Orange Travel. Boeken of betalen kan ik niet; daarvoor verwijs "
            "ik je door.")

ASK = {
    "type": "Waar heb je zin in?",
    "companion": "Met wie ga je op reis?",
    "travelers": "Met hoeveel personen reizen jullie, jijzelf meegerekend?",
    "days": "Hoeveel tijd heb je?",
    "budget": "Wat is je budget per persoon, in euro?",
}

NOT_UNDERSTOOD = ("Dat begrijp ik niet helemaal 🤔 Kies hieronder een optie, of zeg het in je eigen woorden, "
                  "bijvoorbeeld: *binnenland, 3 dagen, met z'n tweeën, €400 p.p.*")
NOT_KNOWN = ("Daar heb ik geen betrouwbare informatie over, dus ik ga niet gokken. Een reisadviseur van "
             "Orange Travel weet het zeker.")
OUT_OF_SCOPE = ("Ik help alleen met tours en reizen van Orange Travel in Suriname, dus daar kan ik je helaas niet "
                "mee helpen. Zal ik een tour voor je zoeken?")
PRIVACY_WARNING = ("⚠️ Ik zag iets wat lijkt op persoonsgegevens ({found}). Deel die alsjeblieft niet in deze chat: "
                   "ik heb ze niet nodig, gebruik ze niet en heb ze direct weggelaten.")
BOOKING = ("Boeken, reserveren, betalen of annuleren kan ik niet voor je doen; ik geef alleen advies. "
           "Je boekt via de knop **Book now** op de tourpagina, of via een reisadviseur.")
HUMAN = (f"Natuurlijk! Een reisadviseur van Orange Travel helpt je graag verder. Bel **{config.CONTACT_PHONE}** "
         "(ma–vr 8:00–19:00, za 12:00–19:00), loop binnen aan de van Sommelsdijckstraat 1 in Paramaribo, "
         "of plan een belafspraak via de contactpagina.")
BYE = "Graag gedaan! Veel plezier in Suriname 🌴 Ik ben er als je nog vragen hebt."
RESTARTED = "Helemaal goed, we beginnen opnieuw ✨"
FOREIGN_CURRENCY = "Ter info: de prijzen van Orange Travel zijn in **euro**, dus ik reken je bedrag als euro."
DOUBT_INTRO = "Geen probleem, ik zet de drie soorten reizen even naast elkaar:"
DOUBT_OUTRO = "Waar voel je het meest voor?"
NO_RESULTS_TO_TALK_ABOUT = "Ik heb nog geen reizen voor je gezocht. Vertel me eerst wat je zoekt, dan kijk ik mee!"
NO_MORE_OPTIONS = ("Meer tours die binnen je budget passen heb ik niet. Je kunt je budget of reisduur aanpassen, "
                   "of een reisadviseur vragen naar een reis op maat.")

RESULTS = {
    3: "Ik heb **3 tours** voor je gevonden! Mijn favoriet is **{best}**.",
    2: "Ik vond **2 tours** binnen je budget. Ik vul de lijst niet aan met tours die te duur zijn.",
    1: "Ik vond **1 tour** binnen je budget. Ik vul de lijst niet aan met tours die te duur zijn.",
}
PARTLY = "Niet alles past precies bij je wensen; bij een **!** zie je wat afwijkt."
OVER_BUDGET = ("Helaas past er niets binnen **{budget} per persoon** 😔 Dit zijn de goedkoopste opties"
               "{type_part}, maar let op: **ze liggen boven je budget**.")
CHANGED = "Ik heb je wens aangepast: {changes}"
WHY_INTRO = "Daarom raad ik **{name}** aan:"
COMPARE_INTRO = "Zo verschillen je opties:"
COMPARE_BEST = "**{name}** past het beste bij je wensen samen: {reason}."

REASONS = {
    "budget_ok": "Binnen je budget: {price} p.p., je houdt {remaining} p.p. over.",
    "budget_over": "Boven je budget: {price} p.p. ({over} p.p. meer).",
    "duration_ok": "De duur past bij je wens ({duration}).",
    "duration_longer": "Duurt langer dan je wens ({duration}).",
    "duration_shorter": "Duurt korter dan je wens ({duration}).",
    "type_ok": "Precies het soort reis dat je zoekt ({type}).",
    "type_other": "Andere soort reis: {type} in plaats van {wish}.",
    "companion_ok": "Geschikt voor {group}.",
    "companion_other": "Niet specifiek bedoeld voor {group}.",
    "min_persons": "Minimaal {min} personen; jullie zijn met {travelers}. Kleinere groepen worden soms samengevoegd of betalen meer.",
    "intensity_high": "Pittige tour: een goede conditie is aan te raden.",
}


def money(value: float) -> str:
    """€1.384 / €27,50 (Dutch notation)."""
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "€" + (text[:-3] if text.endswith(",00") else text)


def days_text(days: float) -> str:
    if days < 1:
        return "een paar uur"
    if days == 1:
        return "1 dag"
    return f"{days:g} dagen".replace(".", ",")


def render_reason(code: str, params: dict) -> str:
    values = dict(params)
    for key in ("price", "remaining", "over"):
        if key in values:
            values[key] = money(values[key])
    if "companion" in values:
        values["group"] = COMPANION_GROUP[values["companion"]]
    return REASONS[code].format(**values)
