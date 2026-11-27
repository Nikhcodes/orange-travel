"""Central configuration: paths, column names, allowed values and the tuned model weights."""

from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
WIDGET_DIR = PROJECT_ROOT / "widget"
DEMO_DIR = PROJECT_ROOT / "demo"
BACKUP_DIR = DATA_DIR / "backups"
TOUR_IMAGES_DIR = ASSETS_DIR / "tours"

TOURS_CSV = DATA_DIR / "tours.csv"
TEST_WISHES_CSV = DATA_DIR / "test_wishes.csv"
INTENTS_CSV = DATA_DIR / "intents.csv"
KNOWLEDGE_CSV = DATA_DIR / "knowledge_base.csv"

# --- Tour columns ----------------------------------------------------------
COL_ID = "id"
COL_NAME = "tour"
COL_TYPE = "type"
COL_PRICE = "prijs_eur"
COL_DURATION_TEXT = "duur"
COL_DAYS_MIN = "dagen_min"
COL_DAYS_MAX = "dagen_max"
COL_MIN_PERSONS = "min_personen"
COL_INTENSITY = "intensiteit"
COL_REGION = "regio"
COL_DESCRIPTION = "beschrijving"
COL_URL = "url"
COL_SUITABILITY_SOURCE = "bron_geschiktheid"
COL_NOTE = "opmerking"

TYPES = ["Stad & omgeving", "Binnenland & natuur", "Rondreis"]
COMPANIONS = ["Alleen", "Stel", "Gezin", "Vrienden"]
COMPANION_COLUMNS = {c: c.lower() for c in COMPANIONS}          # "Gezin" -> column "gezin"
INTENSITIES = ["laag", "gemiddeld", "hoog"]

TOUR_COLUMNS = [
    COL_ID, COL_NAME, COL_TYPE, COL_PRICE, COL_DURATION_TEXT, COL_DAYS_MIN, COL_DAYS_MAX, COL_MIN_PERSONS,
    *COMPANION_COLUMNS.values(), COL_INTENSITY, COL_REGION, COL_DESCRIPTION, COL_URL, COL_SUITABILITY_SOURCE, COL_NOTE,
]
OPTIONAL_TOUR_COLUMNS = [COL_SUITABILITY_SOURCE, COL_NOTE]

# --- Test wish columns -----------------------------------------------------
COL_WISH_ID = "wens_id"
COL_BUDGET = "budget_eur"
COL_WISH_DAYS = "dagen"
COL_WISH_TYPE = "type"
COL_WISH_COMPANION = "gezelschap"
COL_TRAVELERS = "personen"
COL_WISH_KIND = "soort_wens"
COL_EXPECTED = "verwacht"
COL_MOTIVATION = "motivatie"
COL_SPLIT = "set"
SPLIT_DEV, SPLIT_TEST = "ontwikkel", "test"
NO_RESULT_LABEL = "GEEN"

WISH_COLUMNS = [COL_WISH_ID, COL_BUDGET, COL_WISH_DAYS, COL_WISH_TYPE, COL_WISH_COMPANION, COL_TRAVELERS,
                COL_WISH_KIND, COL_EXPECTED, COL_MOTIVATION, COL_SPLIT]

# --- Chat options ----------------------------------------------------------
# Duration choices offered as buttons: label -> days
DURATION_OPTIONS = {
    "Een paar uur": 0.5,
    "Een dag": 1,
    "2–3 dagen": 2.5,
    "4–5 dagen": 4.5,
    "Een week": 7,
    "Twee weken of langer": 16,
}
TOP_N = 3
MAX_TRAVELERS = 20
MIN_TOURS = 15
MIN_WISHES = 30

# --- Source ----------------------------------------------------------------
SITE_URL = "https://www.orangesuriname.com/en/"
CONTACT_URL = "https://www.orangesuriname.com/en/contact-us/"
CUSTOM_TOUR_URL = "https://www.orangesuriname.com/en/custom-tour/"
PAYMENT_URL = "https://www.orangesuriname.com/en/payment-policy/"
PRIVACY_URL = "https://www.orangesuriname.com/en/privacy-policy/"
TOURS_URL = "https://www.orangesuriname.com/en/tours-in-suriname/"
ROUNDTRIPS_URL = "https://www.orangesuriname.com/en/round-trip-suriname/"
CONTACT_PHONE = "+597 421984 / +597 8773397"
DATA_CHECKED = "27 november 2026"

# --- Model weights ---------------------------------------------------------
# Chosen by scripts/tune_weights.py on the 'ontwikkel' wishes only.
# tests/test_evaluation.py checks that these are still the tuning result.
FINAL_WEIGHTS = {"prijs": 1.0, "duur": 4.0, "type": 2.0, "gezelschap": 0.5}
