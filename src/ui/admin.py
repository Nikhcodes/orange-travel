"""Hidden admin window for the project team (URL: /beheer).

Not linked from the client page. Protected with a simple password from
.streamlit/secrets.toml (admin_password); see the developer handbook.

Tabs:
    Testen        paste/upload a test file (or use the built-in wishes) and get all metrics
    Bestemmingen  edit destinations, prices and descriptions; upload photos
    Onderzoek     the three research questions (ablation, model A vs B, tuning)
    Uitleg model  educational explanation with live numbers
"""

import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import config
from src.data_loader import DatasetError, load_destinations, load_test_customers, validate_destinations
from src.evaluation import (REQUIRED_BUDGET_COMPLIANCE, REQUIRED_CATEGORY_MATCH, REQUIRED_TOP3, companion_matrix,
                            evaluate_scenarios, relevance_matrix, results_by_type, summarize)
from src.experiments import ablation, compare_models, split, tune_weights
from src.i18n import format_usd, render_explanation
from src.preprocessing import CustomerProfile
from src.recommendation_engine import RecommendationEngine
from src.rubric import rubric_best
from src.test_file import read_table, recognise
from src.ui import media
from src.ui.model_info import render_model_page
from src.ui.theme import CHART_BLUE, CHART_ORANGE, FONT, LINE, MUTED, NAVY

DEFAULT_PASSWORD = "oranje2026"
MODELS = {
    "Eindmodel (getuned)": None,
    "Model A · prijs + dagen, gewichten 1": {},
    "Model B · zonder prijs": {"prijs": 0.0},
}

ADMIN_CSS = f"""<style>
.ad-kpis {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(160px,1fr)); gap:10px; margin:.5rem 0 1rem 0; }}
.ad-kpi {{ background:white; border:1px solid {LINE}; border-radius:14px; padding:.85rem 1rem; }}
.ad-kpi .l {{ color:{MUTED}; font-size:.78rem; font-weight:650; }}
.ad-kpi .v {{ color:{NAVY}; font-size:1.6rem; font-weight:850; }}
.ad-kpi .f {{ color:{MUTED}; font-size:.74rem; }}
.ad-ok, .ad-no {{ font-size:.7rem; font-weight:800; border-radius:999px; padding:.1rem .45rem; margin-left:.25rem; }}
.ad-ok {{ background:#E6F4EC; color:#1E7F4F; }} .ad-no {{ background:#FDECEC; color:#B42318; }}
.ad-chip {{ display:inline-block; background:white; border:1px solid {LINE}; border-radius:999px; padding:.2rem .6rem;
  margin:0 .3rem .3rem 0; font-size:.82rem; color:{NAVY}; }}
.ot-steps {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr)); gap:10px; margin:.4rem 0 1rem 0; }}
.ot-step {{ background:white; border:1px solid {LINE}; border-top:4px solid #F07913; border-radius:12px; padding:.7rem .85rem; }}
.ot-step .n {{ color:#F07913; font-weight:800; font-size:.8rem; }} .ot-step .t {{ color:{NAVY}; font-weight:700; }}
.ot-step .d {{ color:{MUTED}; font-size:.8rem; }}
</style>"""


# ------------------------------------------------------------------- helpers
def _password() -> str:
    try:
        return str(st.secrets.get("admin_password", DEFAULT_PASSWORD))
    except Exception:  # no secrets.toml present
        return DEFAULT_PASSWORD


def _data_version() -> float:
    """Changes whenever the CSV files change, so cached results refresh automatically."""
    return config.DESTINATIONS_CSV.stat().st_mtime + config.TEST_CUSTOMERS_CSV.stat().st_mtime


@st.cache_data
def _destinations(_version: float) -> pd.DataFrame:
    return load_destinations()


@st.cache_data
def _scenarios(_version: float) -> pd.DataFrame:
    return load_test_customers(destinations=_destinations(_version))


def _engine(weights: dict | None) -> RecommendationEngine:
    return RecommendationEngine(_destinations(_data_version()), weights=weights)


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _kpis(tiles: list[tuple]) -> None:
    html = []
    for label, value, foot, passed in tiles:
        badge = "" if passed is None else (f'<span class="ad-ok">✓ gehaald</span>' if passed
                                           else f'<span class="ad-no">✗ niet gehaald</span>')
        html.append(f'<div class="ad-kpi"><div class="l">{label}</div><div class="v">{value}</div>'
                    f'<div class="f">{foot}{badge}</div></div>')
    st.markdown(f'<div class="ad-kpis">{"".join(html)}</div>', unsafe_allow_html=True)


def _layout(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="white", plot_bgcolor="white",
                      font=dict(family=FONT, color=NAVY, size=13),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    if fig.layout.showlegend is not False and len(fig.data) > 1:
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    return fig


def _heatmap(matrix: pd.DataFrame, x_title: str, y_title: str) -> go.Figure:
    values = matrix.to_numpy()
    row_share = values / values.sum(axis=1, keepdims=True).clip(min=1)   # colour = share within the row
    fig = go.Figure(go.Heatmap(
        z=row_share, customdata=values, x=[str(c) for c in matrix.columns], y=[str(i) for i in matrix.index],
        text=values, texttemplate="%{text}", textfont=dict(size=16), zmin=0, zmax=1,
        colorscale=[[0, "#EEF4FA"], [1, CHART_BLUE]], showscale=False, xgap=3, ygap=3,
        hovertemplate=f"{y_title}: %{{y}}<br>{x_title}: %{{x}}<br>aantal: %{{customdata}}<extra></extra>"))
    fig.update_xaxes(title=x_title, side="top")
    fig.update_yaxes(title=y_title, autorange="reversed")
    return _layout(fig, 320)


# ------------------------------------------------------------------- testing
def _show_evaluation(results: pd.DataFrame, destinations: pd.DataFrame, has_expected: bool) -> None:
    summary = summarize(results)
    tiles = [
        ("Testwensen", summary.total_scenarios, f"{summary.total_recommendations} aanbevelingen", None),
        ("Budget compliance", _pct(summary.budget_compliance), f"eis {_pct(REQUIRED_BUDGET_COMPLIANCE)}", summary.passes_budget),
        ("Soort-match", _pct(summary.category_match), f"eis ≥ {_pct(REQUIRED_CATEGORY_MATCH)}", summary.passes_category),
    ]
    if has_expected:
        tiles += [
            ("Verwachte beste in top 3", f"{summary.top3_hits}/{summary.total_scenarios}",
             f"{_pct(summary.top3_rate)} · eis ≥ {_pct(REQUIRED_TOP3)}", summary.passes_top3),
            ("Verwachte beste op plek 1", f"{summary.top1_hits}/{summary.total_scenarios}", f"{_pct(summary.top1_rate)} · extra", None),
        ]
    _kpis(tiles)

    matrix = relevance_matrix(results, destinations)
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        st.markdown("**Confusion matrix · relevantie** (alle wens × bestemming-paren)")
        st.plotly_chart(_heatmap(matrix.as_frame(), "voorspelling van de bot", "volgens de rubriek"),
                        width="stretch", config={"displayModeBar": False})
        st.caption("Relevant = betaalbaar, juiste soort en passend bij het gezelschap (als zo'n reis bestaat). "
                   "Aanbevolen = in de top 3.")
        _kpis([("Precision", f"{matrix.precision:.2f}", "TP / (TP + FP)", None),
               ("Recall", f"{matrix.recall:.2f}", "TP / (TP + FN)", None),
               ("F1-score", f"{matrix.f1:.2f}", "harmonisch gemiddelde", None),
               ("Accuracy", f"{matrix.accuracy:.2f}", "misleidend: veel TN", None)])
    with right, st.container(border=True):
        st.markdown("**Confusion matrix · reisgezelschap** (gewenst vs. plek 1)")
        st.plotly_chart(_heatmap(companion_matrix(results, destinations), "plek 1 geschikt voor", "klant reist"),
                        width="stretch", config={"displayModeBar": False})
        st.caption("Op de diagonaal = de beste aanbeveling past bij wie er meereist. Buiten de diagonaal: "
                   "er was binnen budget geen passende reis, óf het model koos een andere afweging.")
        if has_expected:
            by_type = results_by_type(results)
            fig = go.Figure()
            for col, name, color in (("top3", "Top 3", CHART_BLUE), ("top1", "Plek 1", CHART_ORANGE)):
                fig.add_trace(go.Bar(y=by_type[config.COL_SCENARIO_TYPE] + " (" + by_type["scenarios"].astype(str) + ")",
                                     x=by_type[col] * 100, name=name, orientation="h", marker=dict(color=color, cornerradius=4),
                                     text=[f"{v * 100:.0f}%" for v in by_type[col]], textposition="outside"))
            fig.update_layout(barmode="group")
            fig.update_xaxes(range=[0, 120], ticksuffix="%")
            fig.update_yaxes(autorange="reversed")
            st.markdown("**Score per type wens**")
            st.plotly_chart(_layout(fig, 260), width="stretch", config={"displayModeBar": False})

    check = {True: "✓", False: "✗"}
    table = pd.DataFrame({
        "Wens": results[config.COL_SCENARIO_ID],
        "Budget": results[config.COL_BUDGET].map(format_usd),
        "Dagen": results[config.COL_WISH_DAYS],
        "Soort": results[config.COL_WISH_CATEGORY],
        "Gezelschap": results[config.COL_WISH_COMPANION],
        "Type": results[config.COL_SCENARIO_TYPE],
        "Verwacht": results[config.COL_EXPECTED],
        "Bot (top 3)": results["recommended"].map(lambda n: ", ".join(n) if n else "— geen advies"),
        "Binnen budget": (results["n_within_budget"] == results["n_recommended"]).map(check),
    })
    if has_expected:
        table["Plek 1"] = results["top1_hit"].map(check)
        table["Top 3"] = results["top3_hit"].map(check)
    only_wrong = has_expected and st.toggle("Toon alleen wensen waar plek 1 afwijkt")
    shown = table[table["Plek 1"] == "✗"] if only_wrong else table
    st.dataframe(shown, hide_index=True, width="stretch", height=min(40 + 35 * len(shown), 560))
    st.download_button("Resultaten downloaden (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name=f"testresultaten_{datetime.now():%Y%m%d_%H%M}.csv", mime="text/csv",
                       icon=":material/download:")


def _tab_testing(destinations: pd.DataFrame, scenarios: pd.DataFrame) -> None:
    st.markdown("Kies een bron. Een eigen bestand mag elke indeling hebben: komma, puntkomma of tab, "
                "Nederlandse of Engelse kolomnamen. De app herkent zelf welke kolom wat is.")
    source = st.segmented_control("Bron", ["Ingebouwde testwensen", "Bestand uploaden", "Tekst plakken"],
                                  default="Ingebouwde testwensen") or "Ingebouwde testwensen"
    model_name = st.selectbox("Model", list(MODELS))
    engine = _engine(MODELS[model_name])

    if source == "Ingebouwde testwensen":
        which = st.radio("Welke wensen?", ["Testset (eindmeting, 30)", "Ontwikkelset (tuning, 30)", "Alle 60"],
                         horizontal=True)
        data = (split(scenarios, config.SPLIT_TEST) if which.startswith("Test")
                else split(scenarios, config.SPLIT_DEV) if which.startswith("Ontwikkel") else scenarios)
        if which.startswith("Ontwikkel") and model_name.startswith("Eindmodel"):
            st.info("Let op: het eindmodel is op deze wensen getuned. Rapporteer de score van de testset.",
                    icon=":material/info:")
        _show_evaluation(evaluate_scenarios(engine, data), destinations, True)
        return

    raw_text = None
    if source == "Bestand uploaden":
        upload = st.file_uploader("Testbestand (.csv of .txt)", type=["csv", "txt", "tsv"])
        raw_text = upload.getvalue() if upload else None
    else:
        raw_text = st.text_area("Plak hier je testwensen (met kopregel)", height=180,
                                placeholder="budget;dagen;soort;gezelschap;verwacht\n1500;7;strand;stel;Solenta Eiland\n300;4;natuur;gezin;geen")
    if not raw_text:
        return
    try:
        raw = read_table(raw_text)
    except Exception as exc:  # pandas raises several parser errors
        st.error(f"Kon de tekst niet als tabel lezen: {exc}")
        return

    recognised = recognise(raw, set(destinations[config.COL_NAME]))
    if recognised.looks_like_destinations:
        st.warning("Dit lijkt een lijst met bestemmingen, geen testwensen. Gebruik daarvoor het tabblad *Bestemmingen*.",
                   icon=":material/warning:")
    chips = "".join(f'<span class="ad-chip"><b>{ours}</b> ← {theirs}</span>' for ours, theirs in recognised.mapping.items())
    st.markdown(f"**Herkende kolommen:** {chips or '—'}", unsafe_allow_html=True)
    if recognised.missing:
        st.error(f"Niet gevonden: {', '.join(recognised.missing)}. Een testbestand heeft minimaal budget, dagen, soort en gezelschap nodig.")
        return
    for problem in recognised.problems:
        st.warning(problem, icon=":material/warning:")
    if not recognised.has_expected:
        st.info("Geen kolom met de verwachte beste bestemming gevonden: alleen budget en soort worden gecontroleerd.",
                icon=":material/info:")
    if recognised.data.empty:
        return
    _show_evaluation(evaluate_scenarios(engine, recognised.data), destinations, recognised.has_expected)


# -------------------------------------------------------------- destinations
def _save_destinations(df: pd.DataFrame) -> None:
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = config.BACKUP_DIR / f"destinations_{datetime.now():%Y%m%d_%H%M%S}.csv"
    shutil.copy(config.DESTINATIONS_CSV, backup)
    df.to_csv(config.DESTINATIONS_CSV, index=False)
    st.cache_data.clear()
    st.cache_resource.clear()


def _label_check(destinations: pd.DataFrame, scenarios_path: Path = config.TEST_CUSTOMERS_CSV) -> list[str]:
    """Wishes whose stored label no longer follows the rubric after a data change."""
    raw = pd.read_csv(scenarios_path)
    wrong = []
    for _, row in raw.iterrows():
        if rubric_best(destinations, row[config.COL_BUDGET], row[config.COL_WISH_DAYS], row[config.COL_WISH_CATEGORY],
                       row[config.COL_WISH_COMPANION]) != row[config.COL_EXPECTED]:
            wrong.append(row[config.COL_SCENARIO_ID])
    return wrong


def _tab_destinations(destinations: pd.DataFrame) -> None:
    st.markdown("Pas bestemmingen, prijzen en beschrijvingen direct in de tabel aan. Voeg onderaan een rij toe of "
                "verwijder rijen. Bij **Opslaan** wordt alles gecontroleerd en wordt eerst een back-up gemaakt.")
    edited = st.data_editor(
        destinations, num_rows="dynamic", hide_index=True, width="stretch", key="dest_editor",
        column_config={
            config.COL_ID: st.column_config.TextColumn("id", help="Uniek, bv. D46. Leeg = automatisch."),
            config.COL_NAME: st.column_config.TextColumn("Bestemming", required=True),
            config.COL_PRICE: st.column_config.NumberColumn("Prijs p.p. (USD)", min_value=1, step=10, format="$%d", required=True),
            config.COL_DAYS: st.column_config.NumberColumn("Dagen", min_value=1, max_value=60, step=1, required=True),
            config.COL_CATEGORY: st.column_config.SelectboxColumn("Soort", options=config.CATEGORIES, required=True),
            config.COL_COMPANION: st.column_config.SelectboxColumn("Geschikt voor", options=config.COMPANIONS, required=True),
            config.COL_DESCRIPTION: st.column_config.TextColumn("Beschrijving (voor de klant)", width="large"),
            config.COL_IMAGE: st.column_config.TextColumn("Afbeelding", disabled=True, help="Upload hieronder een foto."),
        },
    )
    if st.button("Opslaan", type="primary", icon=":material/save:"):
        edited = edited.copy()
        existing = set(edited[config.COL_ID].dropna().astype(str))
        number = 1
        for i in edited.index[edited[config.COL_ID].isna() | (edited[config.COL_ID].astype(str).str.strip() == "")]:
            while f"D{number:02d}" in existing:
                number += 1
            edited.at[i, config.COL_ID] = f"D{number:02d}"
            existing.add(f"D{number:02d}")
        try:
            clean = validate_destinations(edited, "tabel")
        except DatasetError as exc:
            st.error(f"Niet opgeslagen: {exc}")
        else:
            _save_destinations(clean)
            st.success(f"Opgeslagen: {len(clean)} bestemmingen. Back-up staat in data/backups/.", icon=":material/check:")
            wrong = _label_check(clean)
            if wrong:
                st.session_state["labels_outdated"] = wrong

    wrong = st.session_state.get("labels_outdated")
    if wrong:
        st.warning(f"Door de wijziging kloppen {len(wrong)} verwachte uitkomsten in de testwensen niet meer met de "
                   f"rubriek ({', '.join(wrong[:8])}{'…' if len(wrong) > 8 else ''}). Bouw de testwensen opnieuw op "
                   "zodat de evaluatie eerlijk blijft.", icon=":material/warning:")
        if st.button("Testwensen opnieuw opbouwen", icon=":material/autorenew:"):
            from scripts.build_test_scenarios import main as rebuild
            rebuild()
            st.session_state.pop("labels_outdated", None)
            st.cache_data.clear()
            st.success("Testwensen opnieuw opgebouwd met de rubriek.")

    st.divider()
    st.markdown("#### Foto's")
    st.caption("Zonder foto toont de app automatisch een eigen illustratie. Gebruik alleen foto's die jullie zelf "
               "gemaakt hebben of mogen gebruiken, en die niet doen alsof een verzonnen bestemming een echte plek is.")
    names = destinations[config.COL_NAME].tolist()
    choice = st.selectbox("Bestemming", names)
    row = destinations[destinations[config.COL_NAME] == choice].iloc[0]
    left, right = st.columns([1, 1.2], gap="large")
    with left:
        uri = media.destination_image_uri(row[config.COL_ID], row[config.COL_CATEGORY], row[config.COL_IMAGE])
        st.markdown(f'<img src="{uri}" style="width:100%;border-radius:14px;aspect-ratio:16/10;object-fit:cover">',
                    unsafe_allow_html=True)
        st.caption("Huidige foto" if media.uploaded_image_path(row[config.COL_IMAGE]) else "Automatische illustratie")
    with right:
        upload = st.file_uploader("Nieuwe foto (png, jpg, webp)", type=media.ALLOWED_IMAGE_TYPES, key=f"img_{row[config.COL_ID]}")
        if upload and st.button("Foto gebruiken", type="primary", icon=":material/image:"):
            config.DESTINATION_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            ext = Path(upload.name).suffix.lower()
            for old in config.DESTINATION_IMAGES_DIR.glob(f"{row[config.COL_ID]}.*"):
                old.unlink()
            target = config.DESTINATION_IMAGES_DIR / f"{row[config.COL_ID]}{ext}"
            target.write_bytes(upload.getvalue())
            updated = destinations.copy()
            updated.loc[updated[config.COL_ID] == row[config.COL_ID], config.COL_IMAGE] = target.name
            _save_destinations(updated)
            st.rerun()
        if media.uploaded_image_path(row[config.COL_IMAGE]) and st.button("Foto verwijderen", icon=":material/delete:"):
            media.uploaded_image_path(row[config.COL_IMAGE]).unlink()
            updated = destinations.copy()
            updated.loc[updated[config.COL_ID] == row[config.COL_ID], config.COL_IMAGE] = ""
            _save_destinations(updated)
            st.rerun()


# ------------------------------------------------------------------ research
@st.cache_data(show_spinner="Experimenten draaien… (± 30 seconden)")
def _research(_version: float):
    destinations, scenarios = _destinations(_version), _scenarios(_version)
    test = split(scenarios, config.SPLIT_TEST)
    return (ablation(destinations, test, config.FINAL_WEIGHTS),
            compare_models(destinations, scenarios),
            tune_weights(destinations, split(scenarios, config.SPLIT_DEV)).head(10))


def _tab_research() -> None:
    if not st.button("Experimenten uitvoeren", type="primary", icon=":material/science:") and "research_done" not in st.session_state:
        st.caption("Draait alle varianten van het model op de testwensen. Duurt ongeveer een halve minuut.")
        return
    st.session_state["research_done"] = True
    ablation_table, models, tuning = _research(_data_version())

    st.markdown("#### Onderzoeksvraag 1 · Welke wensen bepalen het meest of een reis past?")
    st.caption("Ablatie op de testset: telkens één kenmerk uit de afstandsberekening halen (gewicht 0) en meten hoeveel er misgaat. "
               "Soort ontbreekt hier: dat is ook een hard filter, dus weghalen uit de afstand verandert niets.")
    fig = go.Figure(go.Bar(x=ablation_table["variant"], y=ablation_table["top1"], marker=dict(color=CHART_BLUE, cornerradius=4),
                           text=[f"{v}/{n}" for v, n in zip(ablation_table["top1"], ablation_table["n"])], textposition="outside"))
    fig.update_yaxes(title="verwachte beste op plek 1", range=[0, ablation_table["n"].max() * 1.15])
    st.plotly_chart(_layout(fig, 280), width="stretch", config={"displayModeBar": False})
    st.dataframe(ablation_table, hide_index=True, width="stretch")

    st.markdown("#### Onderzoeksvraag 2 · Wat gebeurt er zonder budget als feature?")
    st.caption("Het harde budgetfilter staat in álle modellen aan. Alleen de afstandsberekening verschilt.")
    pivot = models.pivot(index="model", columns="set", values=["top1", "top3"])
    pivot.columns = [f"{metric} · {split_name}" for metric, split_name in pivot.columns]
    st.dataframe(pivot, width="stretch")
    fig = go.Figure()
    test_rows = models[models["set"] == config.SPLIT_TEST]
    for metric, name, color in (("top3", "Top 3", CHART_BLUE), ("top1", "Plek 1", CHART_ORANGE)):
        fig.add_trace(go.Bar(x=test_rows["model"], y=test_rows[metric], name=name, marker=dict(color=color, cornerradius=4),
                             text=test_rows[metric], textposition="outside"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="aantal van 30 (testset)", range=[0, 34])
    st.plotly_chart(_layout(fig, 300), width="stretch", config={"displayModeBar": False})

    st.markdown("#### Tuning · de 10 beste gewichten op de ontwikkelset")
    st.caption("Gekozen: meeste treffers op plek 1, daarna top 3, daarna de kleinste afwijking van gewicht 1. "
               "De testset is hierbij niet gebruikt.")
    st.dataframe(tuning, hide_index=True, width="stretch")

    st.markdown("#### Onderzoeksvraag 3 · Hoe leg je een klant uit waarom?")
    st.caption("KNN geeft alleen een afstand (een getal). De uitleg vergelijkt de echte waarden van de bestemming met de wens "
               "en meldt ook eerlijk wat níet past.")
    engine = _engine(None)
    example = engine.recommend(CustomerProfile(budget=2500, days=7, category="Strand", companion="Stel"))
    for rec in example.recommendations:
        st.markdown(f"**{rec.rank}. {rec.name}** · afstand {rec.distance:.3f} · {format_usd(rec.price)}")
        st.markdown("\n".join(f"- {line}" for line in render_explanation(rec.reasons, "nl")))


# ---------------------------------------------------------------------- page
def admin_page() -> None:
    st.markdown(ADMIN_CSS, unsafe_allow_html=True)
    top_left, top_right = st.columns([3, 1], vertical_alignment="center")
    with top_left:
        st.markdown(f'<div class="ot-top"><img src="{media.file_uri(media.LOGO)}" alt=""><div><div class="name">'
                    f'Orange Travel · Beheer</div><div class="tag">Alleen voor het projectteam</div></div></div>',
                    unsafe_allow_html=True)

    if not st.session_state.get("admin_ok"):
        with st.form("login"):
            password = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Inloggen", type="primary"):
                if password == _password():
                    st.session_state["admin_ok"] = True
                    st.rerun()
                st.error("Onjuist wachtwoord.")
        return
    with top_right:
        st.link_button("Naar de klantpagina", "/", icon=":material/arrow_back:", width="stretch")

    version = _data_version()
    try:
        destinations, scenarios = _destinations(version), _scenarios(version)
    except DatasetError as exc:
        st.error(f"Dataset-fout: {exc}")
        return

    tabs = st.tabs([":material/fact_check: Testen", ":material/map: Bestemmingen", ":material/science: Onderzoek",
                    ":material/school: Uitleg model"])
    with tabs[0]:
        _tab_testing(destinations, scenarios)
    with tabs[1]:
        _tab_destinations(destinations)
    with tabs[2]:
        _tab_research()
    with tabs[3]:
        render_model_page(_engine(None), "nl")
        weights = ", ".join(f"{k} ×{v:g}" for k, v in config.FINAL_WEIGHTS.items())
        st.caption(f"De waarden in het rekenvoorbeeld zijn geschaald én vermenigvuldigd met de getunede gewichten ({weights}).")
