"""Orange Travel – Intelligent Travel Advisor.

Start with:  uv run streamlit run app.py

Two pages:
    /         the client chatbot (Lora)
    /beheer   hidden admin window for the project team (password protected)
"""

import streamlit as st

from src import config
from src.data_loader import DatasetError, load_destinations
from src.i18n import LANGUAGES
from src.ui import media
from src.ui.admin import admin_page
from src.ui.client import client_page
from src.ui.theme import inject_css

st.set_page_config(
    page_title="Orange Travel · Reisadvies",
    page_icon=str(media.LOVEBIRD),
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()

try:
    load_destinations()
except DatasetError as exc:
    st.error(f"De reisgegevens konden niet worden geladen: {exc}")
    st.stop()

client = st.Page(client_page, title="Orange Travel", url_path="", default=True)
admin = st.Page(admin_page, title="Beheer", url_path="beheer")
navigation = st.navigation([client, admin], position="hidden")

if navigation.url_path != "beheer":
    left, right = st.columns([4, 1.2], vertical_alignment="center")
    with left:
        st.markdown(f'<div class="ot-top"><img src="{media.file_uri(media.LOGO)}" alt="Orange Travel Suriname"></div>',
                    unsafe_allow_html=True)
    with right:
        st.segmented_control("Taal", list(LANGUAGES), key="lang", default="nl", label_visibility="collapsed",
                             format_func=lambda code: "Nederlands" if code == "nl" else "Sranan")

navigation.run()
