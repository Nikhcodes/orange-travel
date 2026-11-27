"""Central configuration: file paths, column names and allowed category values.

Every other module imports its constants from here, so a column name or
category only has to be changed in one place.
"""

from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
DESTINATION_IMAGES_DIR = ASSETS_DIR / "destinations"
BACKUP_DIR = DATA_DIR / "backups"

DESTINATIONS_CSV = DATA_DIR / "destinations.csv"
TEST_CUSTOMERS_CSV = DATA_DIR / "test_customers.csv"

# --- Destination dataset columns -------------------------------------------
COL_ID = "id"
COL_NAME = "bestemming"
COL_PRICE = "prijs_usd"
COL_DAYS = "dagen"
COL_CATEGORY = "soort"
COL_COMPANION = "geschikt_voor"

COL_DESCRIPTION = "beschrijving"   # optional, shown to the client
COL_IMAGE = "afbeelding"           # optional file name in assets/destinations/

DESTINATION_COLUMNS = [COL_ID, COL_NAME, COL_PRICE, COL_DAYS, COL_CATEGORY, COL_COMPANION]
OPTIONAL_DESTINATION_COLUMNS = [COL_DESCRIPTION, COL_IMAGE]

# --- Test scenario columns -------------------------------------------------
COL_SCENARIO_ID = "scenario_id"
COL_BUDGET = "budget_usd"
COL_WISH_DAYS = "dagen"
COL_WISH_CATEGORY = "soort"
COL_WISH_COMPANION = "gezelschap"
COL_SCENARIO_TYPE = "type"
COL_EXPECTED = "expected_best"
COL_MOTIVATION = "motivatie"
COL_SPLIT = "set"                  # "ontwikkel" (tuning) or "test" (final measurement)
SPLIT_DEV = "ontwikkel"
SPLIT_TEST = "test"

SCENARIO_COLUMNS = [
    COL_SCENARIO_ID, COL_BUDGET, COL_WISH_DAYS, COL_WISH_CATEGORY,
    COL_WISH_COMPANION, COL_SCENARIO_TYPE, COL_EXPECTED, COL_MOTIVATION, COL_SPLIT,
]

# Label used in test_customers.csv when no destination fits the budget.
NO_RESULT_LABEL = "GEEN"

# --- Allowed values (fixed order = fixed one-hot column order) -------------
CATEGORIES = ["Strand", "Natuur", "Stad"]
COMPANIONS = ["Alleen", "Stel", "Gezin", "Vrienden"]

# --- Recommendation settings -----------------------------------------------
TOP_N = 3
MIN_DESTINATIONS = 15
MIN_SCENARIOS = 30

# Group size limits used by the chatbot (price is always per person).
MAX_TRAVELERS = 12

# Final feature weights, chosen by scripts/tune_weights.py on the 'ontwikkel'
# wishes only. tests/test_tuning.py checks that these are still the tuning result.
FINAL_WEIGHTS = {"prijs": 0.25, "dagen": 1.0, "soort": 1.0, "gezelschap": 3.0}
