"""Translations (Dutch / Sranan Tongo) and text rendering of explanations.

Two parts:
    - explanation templates (render_reason / render_explanation)
    - interface texts (t)

NOTE: the Sranan Tongo texts must be reviewed by a fluent speaker before the
presentation.
"""

from src.recommendation_engine import Reason

LANGUAGES = {"nl": "Nederlands", "srn": "Sranan Tongo"}
DEFAULT_LANGUAGE = "nl"

# Display labels for dataset values (the CSV values themselves stay Dutch).
CATEGORY_LABELS = {
    "nl": {"Strand": "Strand", "Natuur": "Natuur", "Stad": "Stad"},
    "srn": {"Strand": "Sekanti", "Natuur": "Nâtur", "Stad": "Foto"},
}

# "Suitable for ..." (plural group) and "you travel ..." (manner) forms.
COMPANION_GROUP = {
    "nl": {"Alleen": "solo-reizigers", "Stel": "stellen", "Gezin": "gezinnen", "Vrienden": "vriendengroepen"},
    "srn": {"Alleen": "sma di e reis wawan", "Stel": "koppel", "Gezin": "famiri", "Vrienden": "grupu fu mati"},
}
COMPANION_MANNER = {
    "nl": {"Alleen": "alleen", "Stel": "als stel", "Gezin": "met je gezin", "Vrienden": "met vrienden"},
    "srn": {"Alleen": "wawan", "Stel": "leki koppel", "Gezin": "nanga yu famiri", "Vrienden": "nanga mati"},
}

REASON_TEMPLATES = {
    "nl": {
        "category_match": "Past bij je voorkeur voor {category}.",
        "companion_match": "Geschikt voor {group}.",
        "companion_mismatch": "Let op: bedoeld voor {destination_group}, terwijl jij {manner} reist.",
        "days_exact": "Duurt precies {days} dagen, zoals je wenst.",
        "days_longer": "Duurt {days} dagen: {gap} dag(en) langer dan je wens van {wish}.",
        "days_shorter": "Duurt {days} dagen: {gap} dag(en) korter dan je wens van {wish}.",
        "within_budget": "Kost {price} p.p., binnen je budget van {budget}; je houdt {remaining} over.",
    },
    "srn": {
        "category_match": "A e fiti nanga a sortu reis di yu wani: {category}.",
        "companion_match": "A bun gi {group}.",
        "companion_mismatch": "Luku bun: a meki gi {destination_group}, ma yu e reis {manner}.",
        "days_exact": "A e teki {days} dei, krinkrin leki fa yu wani.",
        "days_longer": "A e teki {days} dei: {gap} dei moro langa leki den {wish} dei di yu wani.",
        "days_shorter": "A e teki {days} dei: {gap} dei moro syatu leki den {wish} dei di yu wani.",
        "within_budget": "A e kosi {price} wan wan sma, ini yu budget fu {budget}; yu e tan abi {remaining}.",
    },
}


def format_usd(amount: float) -> str:
    """Format an amount the Dutch way: 2850 -> '$2.850'."""
    return "$" + f"{int(round(amount)):,}".replace(",", ".")


def render_reason(reason: Reason, lang: str = DEFAULT_LANGUAGE) -> str:
    """Turn one Reason into a sentence in the chosen language."""
    p = reason.params
    values = dict(p)
    if "category" in p:
        values["category"] = CATEGORY_LABELS[lang][p["category"]].lower()
    if reason.code == "companion_match":
        values["group"] = COMPANION_GROUP[lang][p["companion"]]
    if reason.code == "companion_mismatch":
        values["destination_group"] = COMPANION_GROUP[lang][p["destination_companion"]]
        values["manner"] = COMPANION_MANNER[lang][p["companion"]]
    for key in ("price", "budget", "remaining"):
        if key in p:
            values[key] = format_usd(p[key])
    return REASON_TEMPLATES[lang][reason.code].format(**values)


def render_explanation(reasons: list[Reason], lang: str = DEFAULT_LANGUAGE) -> list[str]:
    """Render all reasons of a recommendation."""
    return [render_reason(reason, lang) for reason in reasons]


# ---------------------------------------------------------------------------
# Interface texts (client chatbot)
# ---------------------------------------------------------------------------
COMPANION_LABELS = {
    "nl": {"Alleen": "Alleen", "Stel": "Met z'n tweeën", "Gezin": "Met het gezin", "Vrienden": "Met vrienden"},
    "srn": {"Alleen": "Wawan", "Stel": "Wi tu", "Gezin": "Nanga famiri", "Vrienden": "Nanga mati"},
}
COMPANION_SHORT = {
    "nl": {"Alleen": "Solo", "Stel": "Stel", "Gezin": "Gezin", "Vrienden": "Vrienden"},
    "srn": {"Alleen": "Wawan", "Stel": "Koppel", "Gezin": "Famiri", "Vrienden": "Mati"},
}
CATEGORY_TAGLINES = {
    "nl": {"Strand": "Zon, zee en wit zand", "Natuur": "Jungle, bergen en rivieren", "Stad": "Cultuur, eten en nachtleven"},
    "srn": {"Strand": "Son, se nanga weti santi", "Natuur": "Busi, bergi nanga liba", "Stad": "Kulturu, nyanyan nanga neti-libi"},
}

TEXTS: dict[str, dict[str, str]] = {
    "nl": {
        "bot_name": "Lora",
        "bot_role": "jouw reisadviseur",
        "hero_title": "Ontdek jouw volgende bestemming.",
        "hero_subtitle": "Vertel Lora wat je zoekt. Zij vindt de reizen die passen bij jouw wensen én je budget.",
        "notice": "Studieproject · alle bestemmingen en prijzen zijn fictief en indicatief.",
        # bot lines
        "greet": "Hoi! Ik ben **Lora**, de reisadviseur van Orange Travel. Vier korte vragen en ik zoek de reizen die bij je passen.",
        "ask_category": "Waar heb je zin in?",
        "ask_companion": "Leuk! Met wie ga je op reis?",
        "ask_travelers": "Met hoeveel personen reizen jullie, jijzelf meegerekend?",
        "ask_days": "Hoe lang wil je weg?",
        "ask_budget": "Laatste vraag: wat is je budget?",
        "understood": "Begrepen! Ik heb dit uit je bericht gehaald: {summary}.",
        "not_understood": "Dat heb ik niet helemaal begrepen. Kies hieronder een antwoord, of typ bijvoorbeeld: *strand, met z'n tweeën, 7 dagen, 1500 dollar*.",
        "results_3": "Ik heb **{n} reizen** gevonden die passen. Mijn favoriet voor jou is **{best}**.",
        "results_few": "Ik vond **{n} {trip}** binnen je budget. Ik vul de lijst niet aan met reizen die te duur zijn.",
        "trip_one": "reis", "trip_many": "reizen",
        "no_results": "Helaas, ik heb geen {category_lower}reis gevonden voor {budget} per persoon of minder. Een reis die te duur is raad ik niet aan.",
        "cheapest_label": "Alleen ter informatie · geen advies",
        "cheapest_text": "De goedkoopste {category_lower}reis is **{name}** voor {price} per persoon. Dat is {short} meer dan je budget.",
        # user lines (shown as the customer's answer)
        "u_category": "{category}",
        "u_companion": "{companion}",
        "u_travelers": "{n} personen",
        "u_days": "{days} dagen",
        "u_budget_pp": "{budget} per persoon",
        "u_budget_total": "{total} in totaal ({budget} p.p.)",
        # controls
        "days_weekend": "Weekend", "days_midweek": "Midweek", "days_week": "Een week", "days_10": "10 dagen",
        "days_2weeks": "Twee weken", "days_other": "Ander aantal",
        "days_unit": "dagen",
        "travelers_label": "Aantal personen",
        "next": "Volgende",
        "budget_mode_pp": "Per persoon", "budget_mode_total": "Totaal voor de groep",
        "budget_label": "Budget (USD)",
        "budget_equals_total": "= {total} in totaal voor {n} personen",
        "budget_equals_pp": "= {pp} per persoon",
        "search": "Zoek mijn reizen",
        "chat_placeholder": "Of typ je wens, bijv. 'strand met mijn vriendin, 7 dagen, $1500'",
        "restart": "Opnieuw beginnen",
        "change_budget": "Ander budget",
        "change_category": "Andere soort reis",
        "raise_budget": "Budget naar {price} p.p.",
        "summary_title": "Jouw wensen",
        # result cards
        "badge_best": "Meest aanbevolen",
        "badge_cheapest": "Voordeligst",
        "badge_longest": "Langst genieten",
        "per_person": "per persoon",
        "total_for": "{total} totaal voor {n} personen",
        "remaining": "Je houdt {amount} p.p. over",
        "disclaimer": "Prijzen zijn indicatief en per persoon. Vluchten, visum en beschikbaarheid vallen buiten dit advies.",
        "err_budget_positive": "Vul een budget in dat groter is dan $0.",
        "err_days_positive_int": "Kies een aantal dagen van minimaal 1.",
        "err_category_invalid": "Kies een soort reis.",
        "err_companion_invalid": "Kies met wie je reist.",
    },
    "srn": {
        "bot_name": "Lora",
        "bot_role": "yu reis-adviseur",
        "hero_title": "Feni yu nyun reis-presi.",
        "hero_subtitle": "Taki gi Lora san yu e suku. A o feni den reis di e fiti nanga san yu wani én yu budget.",
        "notice": "Skoro-projekt · ala den presi nanga prijs na pristeri.",
        "greet": "Odi! Mi na **Lora**, a reis-adviseur fu Orange Travel. Fo syatu aksi, dan mi e suku den reis di e fiti yu.",
        "ask_category": "San yu wani du?",
        "ask_companion": "Moi! Nanga suma yu e go?",
        "ask_travelers": "Omeni sma unu e reis, yu srefi okwo?",
        "ask_days": "Omeni dei yu wani go?",
        "ask_budget": "A lasti aksi: omeni na yu budget?",
        "understood": "Mi ferstan! Disi mi feni na ini yu boskopu: {summary}.",
        "not_understood": "Mi no ferstan en heri. Teki wan piki ondro disi, noso skrifi fu eksempre: *sekanti, wi tu, 7 dei, 1500 dalla*.",
        "results_3": "Mi feni **{n} reis** di e fiti. Mi moro lobi gi yu na **{best}**.",
        "results_few": "Mi feni **{n} {trip}** ini yu budget. Mi no e poti reis di de tumsi diri.",
        "trip_one": "reis", "trip_many": "reis",
        "no_results": "Ai, mi no feni wan {category_lower}-reis gi {budget} wan wan sma noso moro pikin. Mi no e rai wan reis di de tumsi diri.",
        "cheapest_label": "Soso fu sabi · a no wan rai",
        "cheapest_text": "A {category_lower}-reis di e kosi a moro pikin moni na **{name}** gi {price} wan wan sma. Dati na {short} moro leki yu budget.",
        "u_category": "{category}",
        "u_companion": "{companion}",
        "u_travelers": "{n} sma",
        "u_days": "{days} dei",
        "u_budget_pp": "{budget} wan wan sma",
        "u_budget_total": "{total} alamala ({budget} wan wan sma)",
        "days_weekend": "Wikènde", "days_midweek": "Midweek", "days_week": "Wan wiki", "days_10": "10 dei",
        "days_2weeks": "Tu wiki", "days_other": "Tra nomru",
        "days_unit": "dei",
        "travelers_label": "Omeni sma",
        "next": "Go doro",
        "budget_mode_pp": "Wan wan sma", "budget_mode_total": "Alamala gi a grupu",
        "budget_label": "Budget (USD)",
        "budget_equals_total": "= {total} alamala gi {n} sma",
        "budget_equals_pp": "= {pp} wan wan sma",
        "search": "Suku mi reis",
        "chat_placeholder": "Noso skrifi san yu wani, fu eks. 'sekanti nanga mi lobi, 7 dei, $1500'",
        "restart": "Bigin baka",
        "change_budget": "Tra budget",
        "change_category": "Tra sortu reis",
        "raise_budget": "Budget go na {price} wan wan sma",
        "summary_title": "San yu wani",
        "badge_best": "Moro bun rai",
        "badge_cheapest": "Moro kownu",
        "badge_longest": "Moro langa",
        "per_person": "wan wan sma",
        "total_for": "{total} alamala gi {n} sma",
        "remaining": "Yu e tan abi {amount} wan wan sma",
        "disclaimer": "Den prijs na fu sabi nomo en de gi wan wan sma. Opolani, visum nanga presi no de ini a rai disi.",
        "err_budget_positive": "Skrifi wan budget di moro bigi leki $0.",
        "err_days_positive_int": "Teki minimaal 1 dei.",
        "err_category_invalid": "Teki wan sortu reis.",
        "err_companion_invalid": "Teki nanga suma yu e reis.",
    },
}

# Labels used on the internal model explanation page (admin).
TEXTS["nl"]["nav_model"] = "Over het model"
TEXTS["srn"]["nav_model"] = "Fa a model e wroko"


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Return an interface text; falls back to Dutch if a key is missing in Sranan Tongo."""
    text = TEXTS.get(lang, {}).get(key) or TEXTS[DEFAULT_LANGUAGE][key]
    return text.format(**kwargs) if kwargs else text
