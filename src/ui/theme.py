"""Visual identity of the client chatbot: colours, CSS, animations and the hero banner.

Colours come from the Orange Travel logo: navy #153147 and lovebird orange #F07913.
All animations respect 'prefers-reduced-motion' (they switch off for people
who have asked their device for less motion).
"""

import streamlit as st

NAVY = "#153147"
NAVY_2 = "#22415E"
ORANGE = "#F07913"
ORANGE_DARK = "#D9640A"
CREAM = "#FFF7EE"
SAND = "#FBEBD6"
GREY_BG = "#F6F4F1"
LINE = "#E8E2DA"
MUTED = "#6A7785"
GOOD = "#1E7F4F"

CHART_BLUE = "#2E6DB4"
CHART_ORANGE = "#D9690B"
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

CSS = f"""
<style>
html, body, [class*="css"] {{ font-family: {FONT}; }}
.stApp {{ background: {GREY_BG}; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
footer {{ visibility: hidden; }}
.block-container {{ max-width: 1120px; padding-top: 1rem; padding-bottom: 7rem; }}
h1, h2, h3, h4 {{ color: {NAVY}; }}
[data-testid="stBottom"] > div {{ background: linear-gradient(to top, {GREY_BG} 70%, transparent); }}

/* ---------- top bar ---------- */
.ot-top {{ display:flex; align-items:center; gap:12px; }}
.ot-top img {{ height: 64px; width:auto; }}
.ot-top .name {{ font-weight: 800; color:{NAVY}; font-size: 1.05rem; letter-spacing:.01em; }}
.ot-top .tag {{ color:{MUTED}; font-size:.78rem; }}

/* ---------- hero ---------- */
.ot-hero {{ position:relative; overflow:hidden; border-radius: 22px; min-height: 250px; margin: .6rem 0 1.4rem 0;
  background: linear-gradient(180deg, {NAVY} 0%, #2C4F73 48%, #E48A3F 100%); color: white; }}
.ot-hero .scene {{ position:absolute; inset:auto 0 0 0; height: 110px; }}
.ot-hero .copy {{ position:relative; z-index:3; padding: 2.1rem 2.4rem 4.6rem 2.4rem; max-width: 520px; }}
.ot-hero .kicker {{ display:inline-flex; align-items:center; gap:.4rem; font-size:.74rem; font-weight:800; letter-spacing:.12em;
  text-transform:uppercase; color:{SAND}; background: rgba(255,255,255,.1); padding:.3rem .7rem; border-radius:999px; }}
.ot-hero h1 {{ color:white; font-size: 2.45rem; line-height:1.08; margin:.7rem 0 .55rem 0; padding:0; font-weight:850; letter-spacing:-.02em; }}
.ot-hero p {{ color: #E9EEF4; font-size:1.05rem; margin:0; }}
.ot-hero .route {{ position:absolute; left:0; top:0; width: 480px; height: 250px; z-index:1; }}
.ot-hero .route path {{ stroke-dasharray: 2 10; animation: ot-dash 18s linear infinite; }}
.ot-hero .bird {{ position:absolute; z-index:2; width: 84px; offset-path: path("M 20 205 C 150 40, 320 30, 455 105");
  offset-rotate: 0deg; animation: ot-fly 9s ease-in-out infinite alternate; filter: drop-shadow(0 6px 10px rgba(0,0,0,.25)); }}
.ot-hero .birdwrap {{ position:absolute; right: 2%; top: 10px; width: 480px; height: 250px; z-index:2; }}
.ot-cloud {{ position:absolute; z-index:1; opacity:.18; animation: ot-drift 40s linear infinite; }}

@keyframes ot-dash {{ to {{ stroke-dashoffset: -240; }} }}
@keyframes ot-fly {{ 0% {{ offset-distance: 8%; }} 100% {{ offset-distance: 92%; }} }}
@keyframes ot-drift {{ from {{ transform: translateX(-80px); }} to {{ transform: translateX(980px); }} }}
@keyframes ot-pop {{ from {{ opacity:0; transform: translateY(8px) scale(.98); }} to {{ opacity:1; transform:none; }} }}
@keyframes ot-rise {{ from {{ opacity:0; transform: translateY(18px); }} to {{ opacity:1; transform:none; }} }}
@keyframes ot-hide {{ to {{ opacity:0; height:0; margin:0; padding:0; }} }}
@keyframes ot-blink {{ 0%,80%,100% {{ opacity:.25; transform: translateY(0); }} 40% {{ opacity:1; transform: translateY(-3px); }} }}
@keyframes ot-bob {{ 0%,100% {{ transform: translateY(0) rotate(-2deg); }} 50% {{ transform: translateY(-4px) rotate(2deg); }} }}

/* ---------- chat ---------- */
.ot-chat {{ display:flex; flex-direction:column; gap: .7rem; }}
.ot-row {{ display:flex; gap:.6rem; align-items:flex-end; }}
.ot-row.user {{ justify-content:flex-end; }}
.ot-avatar {{ width:44px; height:44px; flex:0 0 44px; border-radius:50%; background: white; border: 2px solid {SAND};
  display:flex; align-items:center; justify-content:center; box-shadow: 0 2px 6px rgba(21,49,71,.08); }}
.ot-avatar img {{ width: 34px; height:auto; }}
.ot-row.new .ot-avatar img {{ animation: ot-bob 1.2s ease-in-out 2; }}
.ot-bubble {{ max-width: 78%; padding:.75rem 1rem; border-radius: 18px; font-size: .98rem; line-height:1.45; }}
.ot-row.bot .ot-bubble {{ background: white; color:{NAVY}; border-bottom-left-radius: 6px; box-shadow: 0 1px 2px rgba(21,49,71,.06), 0 4px 14px rgba(21,49,71,.05); }}
.ot-row.user .ot-bubble {{ background: {NAVY}; color: white; border-bottom-right-radius: 6px; }}
.ot-row.new .ot-bubble {{ opacity:0; animation: ot-pop .35s ease-out .75s forwards; }}
.ot-typing {{ display:inline-flex; gap:5px; padding:.9rem 1rem; background:white; border-radius:18px; border-bottom-left-radius:6px;
  animation: ot-hide 0s linear .75s forwards; }}
.ot-typing span {{ width:7px; height:7px; border-radius:50%; background:{ORANGE}; animation: ot-blink 1s infinite; }}
.ot-typing span:nth-child(2) {{ animation-delay:.15s; }} .ot-typing span:nth-child(3) {{ animation-delay:.3s; }}
.ot-newwrap {{ display:flex; flex-direction:column; align-items:flex-start; gap:.4rem; max-width:78%; }}
.ot-newwrap .ot-bubble {{ max-width:100%; }}
.ot-info {{ border:2px dashed #C9B9A6; background:{CREAM}; border-radius:14px; padding:.75rem .95rem; margin-top:.6rem; font-size:.92rem; }}
.ot-info .label {{ font-size:.7rem; font-weight:800; text-transform:uppercase; letter-spacing:.08em; color:{MUTED}; }}

/* answer area */
.st-key-reply {{ background: white; border: 1px solid {LINE}; border-radius: 18px; padding: 1rem 1.1rem 1.1rem 1.1rem;
  margin: .4rem 0 0 54px; box-shadow: 0 6px 22px rgba(21,49,71,.06); animation: ot-rise .4s ease-out .8s both; }}
.st-key-reply button {{ border-radius: 999px; border:1.5px solid {LINE}; font-weight:650; color:{NAVY}; background:white;
  transition: all .15s ease; min-height: 2.6rem; }}
.st-key-reply button:hover {{ border-color:{ORANGE}; color:{ORANGE_DARK}; background:{CREAM}; transform: translateY(-1px); }}
.st-key-reply button[kind="primary"] {{ background:{ORANGE}; border-color:{ORANGE}; color:white; }}
.st-key-reply button[kind="primary"]:hover {{ background:{ORANGE_DARK}; color:white; }}
.ot-tile {{ border-radius: 14px; overflow:hidden; aspect-ratio: 16/10; margin-bottom:.45rem; box-shadow: 0 4px 14px rgba(21,49,71,.12);
  transition: transform .2s ease; }}
.ot-tile img {{ width:100%; height:100%; object-fit:cover; display:block; }}
.ot-tile:hover {{ transform: translateY(-2px); }}
.ot-tagline {{ text-align:center; color:{MUTED}; font-size:.8rem; margin-top:.3rem; }}
.ot-budget-hint {{ color:{MUTED}; font-size:.9rem; margin:-.3rem 0 .6rem 0; }}
.ot-budget-hint b {{ color:{NAVY}; }}

/* ---------- results ---------- */
.ot-summary {{ display:flex; flex-wrap:wrap; gap:.45rem; align-items:center; margin: 1.6rem 0 .9rem 0; }}
.ot-summary .title {{ font-weight:800; color:{NAVY}; margin-right:.3rem; }}
.ot-pill {{ background:white; border:1px solid {LINE}; border-radius:999px; padding:.3rem .75rem; font-size:.85rem; color:{NAVY}; font-weight:600; }}
.ot-card {{ background:white; border-radius: 20px; overflow:hidden; border:1px solid {LINE}; height:100%;
  box-shadow: 0 10px 30px rgba(21,49,71,.08); opacity:0; animation: ot-rise .5s ease-out forwards; transition: transform .2s ease, box-shadow .2s ease; }}
.ot-card:hover {{ transform: translateY(-4px); box-shadow: 0 16px 40px rgba(21,49,71,.14); }}
.ot-card.best {{ border: 2px solid {ORANGE}; }}
.ot-card .img {{ position:relative; aspect-ratio: 16/10; overflow:hidden; }}
.ot-card .img img {{ width:100%; height:100%; object-fit:cover; display:block; transition: transform .6s ease; }}
.ot-card:hover .img img {{ transform: scale(1.04); }}
.ot-badges {{ position:absolute; left:12px; top:12px; display:flex; flex-wrap:wrap; gap:6px; }}
.ot-badge {{ font-size:.74rem; font-weight:800; padding:.32rem .65rem; border-radius:999px; color:white; background:{NAVY};
  box-shadow: 0 2px 8px rgba(0,0,0,.18); display:inline-flex; align-items:center; gap:.3rem; }}
.ot-badge.best {{ background:{ORANGE}; }}
.ot-badge.cheap {{ background:{GOOD}; }}
.ot-card .body {{ padding: 1rem 1.15rem 1.15rem 1.15rem; }}
.ot-card h3 {{ font-size:1.28rem; margin:0; padding:0; font-weight:800; }}
.ot-card .desc {{ color:{MUTED}; font-size:.9rem; margin:.3rem 0 .75rem 0; min-height: 2.6em; }}
.ot-facts {{ display:flex; flex-wrap:wrap; gap:.4rem; margin-bottom:.85rem; }}
.ot-fact {{ background:{GREY_BG}; border-radius:999px; padding:.22rem .65rem; font-size:.8rem; font-weight:650; color:{NAVY}; }}
.ot-price {{ display:flex; align-items:baseline; gap:.4rem; }}
.ot-price .amount {{ font-size:1.7rem; font-weight:850; color:{NAVY}; letter-spacing:-.01em; }}
.ot-price .unit {{ color:{MUTED}; font-size:.85rem; }}
.ot-total {{ color:{NAVY}; font-size:.85rem; font-weight:600; }}
.ot-left {{ display:inline-block; margin-top:.5rem; background:{CREAM}; color:{ORANGE_DARK}; border-radius:8px; padding:.25rem .55rem; font-size:.8rem; font-weight:700; }}
.ot-why {{ list-style:none; padding:0; margin:.8rem 0 0 0; border-top:1px dashed {LINE}; padding-top:.7rem; }}
.ot-why li {{ font-size:.86rem; color:#2C3E50; margin:.3rem 0; padding-left:1.35rem; position:relative; }}
.ot-why li::before {{ position:absolute; left:0; font-weight:900; }}
.ot-why li.pos::before {{ content:"\\2713"; color:{GOOD}; }}
.ot-why li.neg::before {{ content:"!"; color:{ORANGE}; left:.3rem; }}
.ot-disclaimer {{ color:{MUTED}; font-size:.8rem; text-align:center; margin-top:1rem; }}
.st-key-actions button {{ border-radius:999px; font-weight:650; }}

@media (max-width: 1000px) {{ .ot-hero .birdwrap {{ opacity:.35; }} }}
@media (max-width: 760px) {{
  .ot-hero h1 {{ font-size:1.85rem; }}
  .ot-hero .copy {{ padding: 1.5rem 1.4rem 4.2rem 1.4rem; }}
  .ot-hero .birdwrap {{ opacity:.45; }}
  .st-key-reply {{ margin-left: 0; }}
  .ot-bubble {{ max-width: 88%; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration: .01ms !important; animation-delay: 0s !important; animation-iteration-count: 1 !important; transition: none !important; }}
  .ot-hero .bird {{ offset-distance: 70%; }}
}}
</style>
"""

HERO_SCENE = f"""<svg class="scene" viewBox="0 0 1200 110" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M0 70 Q150 40 300 62 T620 58 T900 50 T1200 64 V110 H0Z" fill="#E9A15F" opacity=".55"/>
  <path d="M760 66 q70 -40 150 0Z" fill="{NAVY}" opacity=".55"/>
  <path d="M0 82 Q200 64 420 80 T820 76 T1200 82 V110 H0Z" fill="{NAVY_2}"/>
  <path d="M0 96 Q240 84 520 96 T1200 94 V110 H0Z" fill="{NAVY}"/>
  <g fill="{NAVY}"><path d="M1080 96 q4 -40 -6 -70" stroke="{NAVY}" stroke-width="5" fill="none"/>
  <path d="M1074 26 q-40 -6 -56 18 q30 -10 56 -18Z"/><path d="M1074 26 q36 -14 58 8 q-30 -6 -58 -8Z"/>
  <path d="M1074 26 q-20 22 -40 40 q14 -26 40 -40Z"/><path d="M1074 26 q30 14 40 42 q-20 -24 -40 -42Z"/></g>
</svg>"""

HERO_ROUTE = """<svg class="route" viewBox="0 0 480 250" xmlns="http://www.w3.org/2000/svg">
  <path d="M 20 205 C 150 40, 320 30, 455 105" fill="none" stroke="#FFD6A8" stroke-width="3" stroke-linecap="round"/>
  <circle cx="20" cy="205" r="6" fill="#FFD6A8"/><circle cx="455" cy="105" r="9" fill="none" stroke="#FFD6A8" stroke-width="3"/>
  <circle cx="455" cy="105" r="3.5" fill="#FFD6A8"/>
</svg>"""

CLOUD = """<svg width="120" height="44" viewBox="0 0 120 44" xmlns="http://www.w3.org/2000/svg"><g fill="#FFFFFF">
<ellipse cx="60" cy="30" rx="56" ry="14"/><circle cx="42" cy="22" r="18"/><circle cx="72" cy="16" r="16"/></g></svg>"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
