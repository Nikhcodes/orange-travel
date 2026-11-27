"""Educational content for the 'About the model' page.

The numbers in the worked example (mean, standard deviation, vectors,
distance) are calculated live from the fitted model, so the explanation can
never drift away from what the code actually does.
"""

import numpy as np
import pandas as pd
import streamlit as st

from src import config
from src.i18n import format_usd, t
from src.preprocessing import CustomerProfile
from src.recommendation_engine import RecommendationEngine

EXAMPLE_CUSTOMER = CustomerProfile(budget=3000, days=9, category="Strand", companion="Stel")
EXAMPLE_DESTINATION = "Solenta Eiland"

STEPS = {
    "nl": [
        ("Invoer", "Budget, dagen, soort en gezelschap van de klant."),
        ("One-hot", "Soort en gezelschap worden kolommen met 0 of 1."),
        ("Schalen", "Prijs en dagen krijgen een vergelijkbare schaal."),
        ("KNN", "Afstand van de klant tot alle bestemmingen (met getunede gewichten)."),
        ("Filters", "Te duur of verkeerde soort valt af."),
        ("Top 3", "De dichtstbijzijnde geschikte bestemmingen + uitleg."),
    ],
    "srn": [
        ("Infoeri", "Budget, dei, sortu nanga grupu fu a klanti."),
        ("One-hot", "Sortu nanga grupu e tron kolom nanga 0 noso 1."),
        ("Skali", "Prijs nanga dei e kisi wan skali di kan teki gersi."),
        ("KNN", "A farawe fu a klanti go na ala den presi."),
        ("Filter", "Te diri noso a no a yoisti sortu: a e komoto."),
        ("Top 3", "Den moro krosbei presi di e fiti + eksplikâsi."),
    ],
}

SECTIONS = {
    "nl": {
        "intro": "Deze pagina legt in gewone taal uit hoe de reisadviseur tot een advies komt.",
        "pipeline": "Van invoer tot advies",
        "knn_title": "Wat is K-Nearest Neighbors (KNN)?",
        "knn": (
            "KNN zoekt de **dichtstbijzijnde buren**: de bestemmingen die het meest lijken op wat de klant zoekt. "
            "Je kunt het vergelijken met een reisadviseur die zegt: *“klanten met jouw wensen kozen meestal dit soort reizen.”*\n\n"
            "Elke bestemming en elke klant wordt een rij getallen (een **vector**). KNN meet de **euclidische afstand** "
            "tussen die rijen: het verschil per kenmerk, gekwadrateerd, opgeteld, en daarvan de wortel. "
            "Hoe kleiner de afstand, hoe beter de match.\n\n"
            "Wij gebruiken `NearestNeighbors` van scikit-learn. Dat is een **unsupervised** methode: het model voorspelt "
            "geen label, het zoekt alleen gelijkenis. De testscenario's met een verwachte uitkomst gebruiken we alleen om het model te **evalueren**."
        ),
        "features_title": "Welke kenmerken (features) gebruikt het model?",
        "features": "Elke bestemming en elke klant wordt dezelfde rij van 9 getallen:",
        "scaler_title": "Waarom StandardScaler?",
        "scaler": (
            "Prijs gaat over duizenden dollars, dagen over een handvol. Zonder schalen zou een prijsverschil van $100 "
            "zwaarder wegen dan een verschil van 10 dagen, alleen omdat het getal groter is.\n\n"
            "De StandardScaler rekent elk getal om naar **hoeveel standaardafwijkingen het van het gemiddelde ligt**: "
            "`(waarde − gemiddelde) / standaardafwijking`. De scaler leert gemiddelde en standaardafwijking **alleen uit de bestemmingen** "
            "en gebruikt precies dezelfde getallen voor de klant."
        ),
        "scaler_values": "In onze dataset: prijs gemiddeld {pm}, standaardafwijking {ps} · dagen gemiddeld {dm:.1f}, standaardafwijking {ds:.1f}.",
        "onehot_title": "Waarom one-hot encoding?",
        "onehot": (
            "Een computer kan niet rekenen met het woord “Strand”. Als we Strand=1, Natuur=2, Stad=3 zouden geven, "
            "zou het model denken dat Stad “verder” van Strand ligt dan Natuur; dat is onzin.\n\n"
            "Met one-hot encoding (`pd.get_dummies`) krijgt elke waarde een eigen kolom met 0 of 1. "
            "Alle soorten liggen dan even ver van elkaar af. We leggen de kolomvolgorde vast, zodat een klant altijd "
            "exact dezelfde 9 kolommen krijgt als de bestemmingen."
        ),
        "budget_title": "Hoe werkt het budgetfilter?",
        "budget": (
            "Het budget is een **harde grens**, geen voorkeur. Daarom berekent KNN eerst de afstand tot **alle** bestemmingen. "
            "Daarna vallen alle bestemmingen af die duurder zijn dan het budget of een andere soort hebben. "
            "Van wat overblijft tonen we de dichtstbijzijnde 3 (of minder als er minder zijn).\n\n"
            "Blijft er niets over, dan tonen we **nul aanbevelingen**. De goedkoopste bestemming van die soort laten we alleen "
            "ter informatie zien, duidelijk gemarkeerd als *geen aanbeveling*."
        ),
        "example_title": "Rekenvoorbeeld met echte waarden",
        "example": "Klant: budget {budget}, {days} dagen, Strand, Stel. Het budget wordt gebruikt als gewenst prijsniveau. Vergeleken met **{dest}**:",
        "example_result": "Euclidische afstand = √(som van de kwadraten) = √{sq:.3f} = **{dist:.3f}**",
        "col_feature": "Kenmerk", "col_customer": "Klant", "col_dest": "Bestemming", "col_sq": "Verschil²",
    },
    "srn": {
        "intro": "A bladzijde disi e taki na pristeri tongo fa a reis-rai e kisi wan rai.",
        "pipeline": "Fu infoeri te go na rai",
        "knn_title": "San na K-Nearest Neighbors (KNN)?",
        "knn": (
            "KNN e suku den **moro krosbei birati**: den presi di moro gersi san a klanti e suku. "
            "A gersi wan reis-adviseur di e taki: *“klanti nanga den srefi winsi ben teki den sortu reis disi.”*\n\n"
            "Ibri presi nanga ibri klanti e tron wan rij nomru (wan **vector**). KNN e mete a **euclidische farawe** "
            "fu den rij disi. Fa a farawe moro pikin, fa a match moro bun.\n\n"
            "Wi e gebroiki `NearestNeighbors` fu scikit-learn. Disi na wan **unsupervised** fasi: a model no e taki wan label "
            "fosi, a e suku soso san gersi. Den tesi-situwâsi wi e gebroiki soso fu **tesi** a model."
        ),
        "features_title": "Sortu kenmerk a model e gebroiki?",
        "features": "Ibri presi nanga ibri klanti e tron a srefi rij fu 9 nomru:",
        "scaler_title": "Fu san ede StandardScaler?",
        "scaler": (
            "Prijs e go te na dusun dalla, dei na wan pikin nomru nomo. Sondro skali, wan prijs-verschil fu $100 "
            "ben o weigi moro leki 10 dei, soso fu di a nomru moro bigi.\n\n"
            "A StandardScaler e kenki ibri nomru na **omeni standaardafwijking a de fu a gemiddeld**. "
            "A scaler e leri gemiddeld nanga standaardafwijking **soso fu den presi** en e gebroiki den srefi nomru gi a klanti."
        ),
        "scaler_values": "Ini wi dataset: prijs gemiddeld {pm}, standaardafwijking {ps} · dei gemiddeld {dm:.1f}, standaardafwijking {ds:.1f}.",
        "onehot_title": "Fu san ede one-hot encoding?",
        "onehot": (
            "Wan kompyuta no man reken nanga a wortu “Strand”. Efu wi gi Strand=1, Natuur=2, Stad=3, "
            "a model ben o denki taki Stad de moro fara fu Strand leki Natuur; dati no tru.\n\n"
            "Nanga one-hot encoding (`pd.get_dummies`) ibri sortu e kisi en eigi kolom nanga 0 noso 1. "
            "Wi e seti a kolom-orde, so taki wan klanti e kisi den srefi 9 kolom leki den presi."
        ),
        "budget_title": "Fa a budget-filter e wroko?",
        "budget": (
            "A budget na wan **tranga grens**. Fosi KNN e reken a farawe go na **ala** den presi. "
            "Baka dati ala presi di moro diri leki a budget, noso di abi wan tra sortu, e komoto. "
            "Fu san e tan, wi e sori den 3 moro krosbei (noso moro mendri).\n\n"
            "Efu noti no e tan, wi e sori **0 rai**. A presi di e kosi a moro pikin moni wi e sori soso fu sabi, "
            "nanga krin taki *a no wan rai*."
        ),
        "example_title": "Reken-eksempre nanga tru nomru",
        "example": "Klanti: budget {budget}, {days} dei, Strand, Koppel. A budget e wroko leki a prijs di a klanti wani. Teki na sei **{dest}**:",
        "example_result": "Euclidische farawe = √(som fu den kwadraat) = √{sq:.3f} = **{dist:.3f}**",
        "col_feature": "Kenmerk", "col_customer": "Klanti", "col_dest": "Presi", "col_sq": "Verschil²",
    },
}


def render_model_page(engine: RecommendationEngine, lang: str) -> None:
    text = SECTIONS[lang]
    st.caption(text["intro"])
    st.markdown(f"##### {text['pipeline']}")
    steps = "".join(
        f'<div class="ot-step"><div class="n">{i}</div><div class="t">{title}</div><div class="d">{desc}</div></div>'
        for i, (title, desc) in enumerate(STEPS[lang], start=1)
    )
    st.markdown(f'<div class="ot-steps">{steps}</div>', unsafe_allow_html=True)

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            st.markdown(f"#### {text['knn_title']}")
            st.markdown(text["knn"])
        with st.container(border=True):
            st.markdown(f"#### {text['onehot_title']}")
            st.markdown(text["onehot"])
    with right:
        with st.container(border=True):
            st.markdown(f"#### {text['scaler_title']}")
            st.markdown(text["scaler"])
            scaler = engine.preprocessor.scaler
            st.caption(
                text["scaler_values"].format(
                    pm=format_usd(scaler.mean_[0]), ps=format_usd(scaler.scale_[0]),
                    dm=scaler.mean_[1], ds=scaler.scale_[1],
                )
            )
        with st.container(border=True):
            st.markdown(f"#### {text['budget_title']}")
            st.markdown(text["budget"])

    with st.container(border=True):
        st.markdown(f"#### {text['features_title']}")
        st.markdown(text["features"])
        st.code("\n".join(engine.preprocessor.feature_columns), language=None)

    with st.container(border=True):
        st.markdown(f"#### {text['example_title']}")
        st.markdown(text["example"].format(
            budget=format_usd(EXAMPLE_CUSTOMER.budget), days=EXAMPLE_CUSTOMER.days, dest=EXAMPLE_DESTINATION))
        customer_vec = engine.preprocessor.transform_customer(EXAMPLE_CUSTOMER).iloc[0]
        index = engine.destinations.index[engine.destinations[config.COL_NAME] == EXAMPLE_DESTINATION][0]
        dest_vec = engine.destination_features.iloc[index]
        squared = (customer_vec - dest_vec) ** 2
        table = pd.DataFrame({
            text["col_feature"]: engine.preprocessor.feature_columns,
            text["col_customer"]: customer_vec.round(3).to_numpy(),
            text["col_dest"]: dest_vec.round(3).to_numpy(),
            text["col_sq"]: squared.round(3).to_numpy(),
        })
        st.dataframe(table, hide_index=True, width="stretch")
        st.markdown(text["example_result"].format(sq=float(squared.sum()), dist=float(np.sqrt(squared.sum()))))
