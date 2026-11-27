"""Team dashboard (not for customers): test, evaluate and manage Sabi.

Start:  uv run streamlit run dashboard.py      ->  http://localhost:8501
Password: admin_password in .streamlit/secrets.toml (default: oranje2026)

Tabs
    Advies testen   built-in test wishes or a pasted/uploaded file -> success criteria + confusion matrix
    Intentmodel     confusion matrix, precision/recall/F1 per intent, try a sentence
    Tours beheren   edit tours and prices (validated, with backup), upload photos
    Onderzoek       research questions 1-3: ablation, model A vs B, tuning
    Requirements    which requirement is built where and tested how
"""

import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import config, texts
from src.data_loader import DatasetError, load_test_wishes, load_tours, validate_tours
from src.evaluation import (REQUIRED_BUDGET_COMPLIANCE, REQUIRED_TOP3, REQUIRED_TYPE_MATCH, evaluate_wishes,
                            relevance_matrix, results_by_kind, summarize)
from src.experiments import ablation, compare_models, split, tune_weights
from src.nlu.intent_classifier import train_and_evaluate
from src.nlu.privacy import check_privacy
from src.nlu.understanding import Understander
from src.recommendation_engine import RecommendationEngine
from src.rubric import rubric_best
from src.test_file import read_table, recognise

NAVY, ORANGE, BLUE, LINE = "#153147", "#D9690B", "#2E6DB4", "#E8E2DA"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif"
DEFAULT_PASSWORD = "oranje2026"
MODELS = {"Eindmodel (getuned)": None, "Model A · alle gewichten 1": {}, "Model B · zonder prijs": {"prijs": 0.0}}

st.set_page_config(page_title="Sabi · teamdashboard", page_icon=str(config.WIDGET_DIR / "sabi.svg"), layout="wide")
st.markdown(f"""<style>
.block-container {{ max-width: 1200px; padding-top: 1.2rem; }}
.kpis {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(170px,1fr)); gap:10px; margin:.4rem 0 1rem 0; }}
.kpi {{ background:white; border:1px solid {LINE}; border-radius:14px; padding:.8rem 1rem; }}
.kpi .l {{ color:#6a7785; font-size:.8rem; font-weight:650; }} .kpi .v {{ color:{NAVY}; font-size:1.6rem; font-weight:850; }}
.kpi .f {{ color:#6a7785; font-size:.75rem; }}
.ok, .no {{ font-size:.7rem; font-weight:800; border-radius:999px; padding:.1rem .45rem; margin-left:.3rem; }}
.ok {{ background:#E6F4EC; color:#1E7F4F; }} .no {{ background:#FDECEC; color:#B42318; }}
.chip {{ display:inline-block; background:white; border:1px solid {LINE}; border-radius:999px; padding:.15rem .6rem; margin:0 .3rem .3rem 0; font-size:.82rem; }}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers
def password() -> str:
    try:
        return str(st.secrets.get("admin_password", DEFAULT_PASSWORD))
    except Exception:
        return DEFAULT_PASSWORD


def version() -> float:
    return config.TOURS_CSV.stat().st_mtime + config.TEST_WISHES_CSV.stat().st_mtime + config.INTENTS_CSV.stat().st_mtime


@st.cache_data
def tours(_v: float) -> pd.DataFrame:
    return load_tours()


@st.cache_data
def wishes(_v: float) -> pd.DataFrame:
    return load_test_wishes(tours=tours(_v))


@st.cache_resource
def understander(_v: float) -> Understander:
    return Understander()


@st.cache_data
def intent_eval(_v: float):
    return train_and_evaluate()


def kpis(items: list[tuple]) -> None:
    html = []
    for label, value, foot, passed in items:
        badge = "" if passed is None else ('<span class="ok">✓ gehaald</span>' if passed else '<span class="no">✗ niet gehaald</span>')
        html.append(f'<div class="kpi"><div class="l">{label}</div><div class="v">{value}</div><div class="f">{foot}{badge}</div></div>')
    st.markdown(f'<div class="kpis">{"".join(html)}</div>', unsafe_allow_html=True)


def layout(fig: go.Figure, height: int = 320) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40 if len(fig.data) > 1 else 10, b=10),
                      paper_bgcolor="white", plot_bgcolor="white", font=dict(family=FONT, color=NAVY, size=13),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    return fig


def heatmap(matrix: pd.DataFrame, x_title: str, y_title: str, height: int = 340) -> go.Figure:
    values = matrix.to_numpy()
    share = values / values.sum(axis=1, keepdims=True).clip(min=1)
    fig = go.Figure(go.Heatmap(z=share, customdata=values, x=[str(c) for c in matrix.columns], y=[str(i) for i in matrix.index],
                               text=values, texttemplate="%{text}", zmin=0, zmax=1, showscale=False, xgap=2, ygap=2,
                               colorscale=[[0, "#EEF4FA"], [1, BLUE]],
                               hovertemplate=f"{y_title}: %{{y}}<br>{x_title}: %{{x}}<br>aantal: %{{customdata}}<extra></extra>"))
    fig.update_xaxes(title=x_title, side="top")
    fig.update_yaxes(title=y_title, autorange="reversed")
    return layout(fig, height)


def pct(x: float) -> str:
    return f"{x * 100:.0f}%"


# ------------------------------------------------------------- tab: advice
def show_evaluation(results: pd.DataFrame, tour_df: pd.DataFrame, has_expected: bool) -> None:
    s = summarize(results)
    items = [("Testwensen", s.total_wishes, f"{s.total_recommendations} aanbevelingen", None),
             ("Binnen budget", pct(s.budget_compliance), f"eis {pct(REQUIRED_BUDGET_COMPLIANCE)}", s.passes_budget),
             ("Soort reis klopt", pct(s.type_match), f"eis ≥ {pct(REQUIRED_TYPE_MATCH)}", s.passes_type)]
    if has_expected:
        items += [("Verwachte tour in top 3", f"{s.top3_hits}/{s.total_wishes}", f"{pct(s.top3_rate)} · eis ≥ {pct(REQUIRED_TOP3)}", s.passes_top3),
                  ("Verwachte tour op plek 1", f"{s.top1_hits}/{s.total_wishes}", f"{pct(s.top1_rate)} · extra", None)]
    items.append(("FR-12: tours boven budget getoond", s.over_budget_shown, "altijd gemarkeerd, telt niet als advies", None))
    kpis(items)
    left, right = st.columns(2, gap="medium")
    with left, st.container(border=True):
        m = relevance_matrix(results, tour_df)
        st.markdown("**Confusion matrix · relevantie** (alle wens × tour-paren)")
        st.plotly_chart(heatmap(m.as_frame(), "advies van Sabi", "volgens de rubriek"), width="stretch", config={"displayModeBar": False})
        kpis([("Precision", f"{m.precision:.2f}", "TP / (TP+FP)", None), ("Recall", f"{m.recall:.2f}", "TP / (TP+FN)", None),
              ("F1", f"{m.f1:.2f}", "harmonisch gemiddelde", None), ("Accuracy", f"{m.accuracy:.2f}", "misleidend: veel TN", None)])
    with right, st.container(border=True):
        if has_expected:
            st.markdown("**Score per soort wens**")
            by = results_by_kind(results)
            fig = go.Figure()
            for col, name, color in (("top3", "Top 3", BLUE), ("top1", "Plek 1", ORANGE)):
                fig.add_trace(go.Bar(y=by[config.COL_WISH_KIND] + " (" + by["wensen"].astype(str) + ")", x=by[col] * 100, name=name,
                                     orientation="h", marker=dict(color=color, cornerradius=4),
                                     text=[f"{v * 100:.0f}%" for v in by[col]], textposition="outside"))
            fig.update_layout(barmode="group")
            fig.update_xaxes(range=[0, 120], ticksuffix="%")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(layout(fig, 360), width="stretch", config={"displayModeBar": False})
        else:
            st.info("Zonder kolom 'verwacht' worden alleen budget en soort reis gecontroleerd.")
    check = {True: "✓", False: "✗"}
    table = pd.DataFrame({
        "Wens": results[config.COL_WISH_ID], "Budget p.p.": results[config.COL_BUDGET].map(texts.money),
        "Dagen": results[config.COL_WISH_DAYS], "Soort": results[config.COL_WISH_TYPE],
        "Gezelschap": results[config.COL_WISH_COMPANION], "Pers.": results[config.COL_TRAVELERS],
        "Soort wens": results[config.COL_WISH_KIND], "Verwacht": results[config.COL_EXPECTED],
        "Sabi (top 3)": results["aanbevolen"].map(lambda n: ", ".join(n) if n else "— geen advies (FR-12 alternatieven)"),
    })
    if has_expected:
        table["Plek 1"], table["Top 3"] = results["top1_hit"].map(check), results["top3_hit"].map(check)
        if st.toggle("Toon alleen wensen waar plek 1 afwijkt"):
            table = table[table["Plek 1"] == "✗"]
    st.dataframe(table, hide_index=True, width="stretch", height=min(40 + 35 * len(table), 560))
    st.download_button("Resultaten downloaden (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name=f"testresultaten_{datetime.now():%Y%m%d_%H%M}.csv", icon=":material/download:")


def tab_advice(tour_df: pd.DataFrame, wish_df: pd.DataFrame) -> None:
    st.caption("Een eigen bestand mag elke indeling hebben (komma, puntkomma of tab; Nederlandse of Engelse kolomnamen).")
    source = st.segmented_control("Bron", ["Ingebouwde testwensen", "Bestand uploaden", "Tekst plakken"],
                                  default="Ingebouwde testwensen") or "Ingebouwde testwensen"
    model = st.selectbox("Model", list(MODELS))
    engine = RecommendationEngine(tour_df, weights=MODELS[model])
    if source == "Ingebouwde testwensen":
        which = st.radio("Welke wensen?", ["Testset (eindmeting, 30)", "Ontwikkelset (tuning, 30)", "Alle 60"], horizontal=True)
        data = split(wish_df, config.SPLIT_TEST) if which.startswith("Test") else (
            split(wish_df, config.SPLIT_DEV) if which.startswith("Ontwikkel") else wish_df)
        if which.startswith("Ontwikkel") and model.startswith("Eindmodel"):
            st.info("Het eindmodel is op deze wensen getuned. Rapporteer de score van de testset.", icon=":material/info:")
        show_evaluation(evaluate_wishes(engine, data), tour_df, True)
        return
    raw = None
    if source == "Bestand uploaden":
        upload = st.file_uploader("Testbestand (.csv / .txt)", type=["csv", "txt", "tsv"])
        raw = upload.getvalue() if upload else None
    else:
        raw = st.text_area("Plak je testwensen (met kopregel)", height=170,
                           placeholder="budget;dagen;soort;gezelschap;personen;verwacht\n400;2.5;binnenland;stel;2;Myrysji Lodge\n20;1;stad;gezin;4;geen")
    if not raw:
        return
    try:
        table = read_table(raw)
    except Exception as exc:
        st.error(f"Kon de tekst niet als tabel lezen: {exc}")
        return
    rec = recognise(table, set(tour_df[config.COL_NAME]))
    if rec.looks_like_tours:
        st.warning("Dit lijkt een tourlijst, geen testwensen. Gebruik daarvoor het tabblad Tours beheren.")
    st.markdown("**Herkende kolommen:** " + ("".join(f'<span class="chip"><b>{o}</b> ← {t}</span>' for o, t in rec.mapping.items()) or "—"),
                unsafe_allow_html=True)
    if rec.missing:
        st.error(f"Niet gevonden: {', '.join(rec.missing)}. Minimaal nodig: budget, dagen, soort en gezelschap.")
        return
    for problem in rec.problems:
        st.warning(problem)
    if not rec.data.empty:
        show_evaluation(evaluate_wishes(engine, rec.data), tour_df, rec.has_expected)


# ------------------------------------------------------------ tab: intents
def tab_intents(v: float) -> None:
    e = intent_eval(v)
    st.caption(f"Supervised ML (TF-IDF + logistische regressie). Getraind op {e.n_train} zinnen, getest op {e.n_test} zinnen "
               "die het model niet gezien heeft (gestratificeerde split 75/25).")
    kpis([("Accuracy (test)", f"{e.accuracy:.2f}", "aandeel goed geraden", None),
          ("Macro F1 (test)", f"{e.macro_f1:.2f}", "gemiddelde over alle intenties", None),
          ("Intenties", len(e.labels), "klassen", None), ("Fouten in test", len(e.errors), f"van {e.n_test}", None)])
    with st.container(border=True):
        st.markdown("**Confusion matrix · intentmodel**")
        st.plotly_chart(heatmap(e.matrix, "voorspeld", "echt", 520), width="stretch", config={"displayModeBar": False})
    left, right = st.columns(2)
    with left:
        st.markdown("**Precision, recall en F1 per intentie**")
        st.dataframe(e.report.drop(index=["accuracy"], errors="ignore"), width="stretch")
    with right:
        st.markdown("**Fout geclassificeerd (testset)**")
        st.dataframe(e.errors, hide_index=True, width="stretch", height=420)
    st.markdown("#### Probeer een zin")
    sentence = st.text_input("Zin", placeholder="bv. heb je iets goedkopers voor 2 dagen in de jungle?")
    if sentence:
        privacy = check_privacy(sentence)
        result = understander(v).understand(privacy.clean_text)
        st.write({"intentie": result.intent, "zekerheid": round(result.confidence, 2), "begrepen": result.understood,
                  "via vangnetregel": result.by_rule, "gevonden wensen": {k: getattr(result.slots, k) for k in
                  ("tour_type", "companion", "travelers", "days", "budget", "budget_is_total")},
                  "persoonsgegevens": privacy.found or "geen"})


# --------------------------------------------------------------- tab: tours
def save_tours(df: pd.DataFrame) -> None:
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(config.TOURS_CSV, config.BACKUP_DIR / f"tours_{datetime.now():%Y%m%d_%H%M%S}.csv")
    df.to_csv(config.TOURS_CSV, index=False)
    st.cache_data.clear()
    st.cache_resource.clear()


def tab_tours(tour_df: pd.DataFrame) -> None:
    st.caption("Pas tours, prijzen en beschrijvingen aan. Bij Opslaan wordt alles gecontroleerd en eerst een back-up gemaakt. "
               "De API-server laadt de data bij een herstart opnieuw.")
    edited = st.data_editor(tour_df, num_rows="dynamic", hide_index=True, width="stretch", column_config={
        config.COL_TYPE: st.column_config.SelectboxColumn("type", options=config.TYPES, required=True),
        config.COL_INTENSITY: st.column_config.SelectboxColumn("intensiteit", options=config.INTENSITIES, required=True),
        config.COL_PRICE: st.column_config.NumberColumn("prijs_eur", min_value=1, format="€%.2f", required=True),
        config.COL_URL: st.column_config.LinkColumn("url"),
        **{c: st.column_config.CheckboxColumn(c) for c in config.COMPANION_COLUMNS.values()},
    })
    if st.button("Opslaan", type="primary", icon=":material/save:"):
        edited = edited.copy()
        for c in config.COMPANION_COLUMNS.values():
            edited[c] = edited[c].astype(int)
        try:
            clean = validate_tours(edited, "tabel")
        except DatasetError as exc:
            st.error(f"Niet opgeslagen: {exc}")
        else:
            save_tours(clean)
            st.success("Opgeslagen. Back-up in data/backups/.")
            raw = pd.read_csv(config.TEST_WISHES_CSV)
            wrong = [r[config.COL_WISH_ID] for _, r in raw.iterrows() if rubric_best(
                clean, r[config.COL_BUDGET], r[config.COL_WISH_DAYS], r[config.COL_WISH_TYPE], r[config.COL_WISH_COMPANION]) != r[config.COL_EXPECTED]]
            if wrong:
                st.warning(f"Door de wijziging kloppen {len(wrong)} verwachte uitkomsten niet meer met de rubriek "
                           f"({', '.join(wrong[:8])}). Draai `uv run python -m scripts.build_test_wishes` en daarna "
                           "`uv run python -m scripts.tune_weights` vóór je nieuwe cijfers rapporteert.")
    st.divider()
    st.markdown("#### Foto per tour")
    st.caption("Zonder foto toont Sabi een eigen illustratie. Gebruik alleen foto's waarvoor jullie toestemming hebben.")
    choice = st.selectbox("Tour", tour_df[config.COL_NAME])
    tour_id = tour_df.loc[tour_df[config.COL_NAME] == choice, config.COL_ID].iloc[0]
    current = next((p for p in config.TOUR_IMAGES_DIR.glob(f"{tour_id}.*")), None) if config.TOUR_IMAGES_DIR.exists() else None
    left, right = st.columns(2)
    with left:
        if current:
            st.image(str(current), caption="Huidige foto")
        else:
            st.caption("Nu: automatische illustratie")
    with right:
        upload = st.file_uploader("Nieuwe foto", type=["jpg", "jpeg", "png", "webp"], key=f"photo_{tour_id}")
        if upload and st.button("Foto gebruiken", icon=":material/image:"):
            config.TOUR_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            for old in config.TOUR_IMAGES_DIR.glob(f"{tour_id}.*"):
                old.unlink()
            (config.TOUR_IMAGES_DIR / f"{tour_id}{Path(upload.name).suffix.lower()}").write_bytes(upload.getvalue())
            st.rerun()
        if current and st.button("Foto verwijderen", icon=":material/delete:"):
            current.unlink()
            st.rerun()


# ------------------------------------------------------------ tab: research
@st.cache_data(show_spinner="Experimenten draaien… (± 1 minuut)")
def research(_v: float):
    t, w = tours(_v), wishes(_v)
    return (ablation(t, split(w, config.SPLIT_TEST), config.FINAL_WEIGHTS), compare_models(t, w),
            tune_weights(t, split(w, config.SPLIT_DEV)).head(10))


def tab_research(v: float) -> None:
    if not st.button("Experimenten uitvoeren", type="primary", icon=":material/science:") and "research" not in st.session_state:
        st.caption("Draait alle modelvarianten op de testwensen.")
        return
    st.session_state["research"] = True
    abl, models, tuning = research(v)
    st.markdown("#### Onderzoeksvraag 1 · Welke wensen bepalen het meest of een reis past?")
    fig = go.Figure(go.Bar(x=abl["variant"], y=abl["top1"], marker=dict(color=BLUE, cornerradius=4),
                           text=[f"{a}/{n}" for a, n in zip(abl["top1"], abl["n"])], textposition="outside"))
    fig.update_yaxes(title="verwachte tour op plek 1 (testset)", range=[0, 34])
    st.plotly_chart(layout(fig, 280), width="stretch", config={"displayModeBar": False})
    st.dataframe(abl, hide_index=True, width="stretch")
    st.markdown("#### Onderzoeksvraag 2 · Wat gebeurt er zonder budget als feature?")
    st.caption("De budgetregel staat in álle modellen aan; alleen de afstandsberekening verschilt.")
    st.dataframe(models, hide_index=True, width="stretch")
    st.markdown("#### Tuning · de 10 beste gewichten op de ontwikkelset")
    st.dataframe(tuning, hide_index=True, width="stretch")
    st.markdown("#### Onderzoeksvraag 3 · Hoe leg je uit waarom?")
    st.caption("KNN geeft alleen een afstand. Sabi vergelijkt de echte tourgegevens met de wens en noemt ook wat níet past (FR-11).")


# ---------------------------------------------------------------------- page
def main() -> None:
    st.markdown("## 🐦 Sabi · teamdashboard")
    if not st.session_state.get("ok"):
        with st.form("login"):
            pw = st.text_input("Wachtwoord", type="password")
            if st.form_submit_button("Inloggen", type="primary"):
                if pw == password():
                    st.session_state["ok"] = True
                    st.rerun()
                st.error("Onjuist wachtwoord.")
        return
    v = version()
    try:
        tour_df, wish_df = tours(v), wishes(v)
    except DatasetError as exc:
        st.error(f"Dataset-fout: {exc}")
        return
    tabs = st.tabs([":material/fact_check: Advies testen", ":material/psychology: Intentmodel", ":material/map: Tours beheren",
                    ":material/science: Onderzoek", ":material/checklist: Requirements"])
    with tabs[0]:
        tab_advice(tour_df, wish_df)
    with tabs[1]:
        tab_intents(v)
    with tabs[2]:
        tab_tours(tour_df)
    with tabs[3]:
        tab_research(v)
    with tabs[4]:
        doc = config.PROJECT_ROOT / "docs" / "requirements.md"
        st.markdown(doc.read_text(encoding="utf-8") if doc.exists() else "docs/requirements.md ontbreekt.")


main()
