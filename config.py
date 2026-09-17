"""
config.py — a single place for every constant and setting used across
the pipeline.

Before this file existed, REQUIRED_COLUMNS lived in extract.py while
VALID_TRANSACTION_TYPES and VALID_CURRENCY lived in validate.py, and
folder names were hardcoded again in pipeline.py. Scattering constants
like this means a single business rule change (e.g. accepting a new
currency) requires hunting across multiple files to find every place
it's mentioned — and it's easy to update one copy and miss another.

Pulling everything into one file doesn't change any behavior; it just
gives every other module ONE place to import shared settings from.
"""

# --- Folder locations ---
INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"

# --- File discovery ---
# Branch files must match this pattern: BR<digits>_<date>_TRANSACTION.csv
BRANCH_FILE_PATTERN = "BR*_*_TRANSACTION.csv"

# --- Required schema ---
REQUIRED_COLUMNS = [
    "transaction_id",
    "account_id",
    "transaction_date",
    "transaction_type",
    "amount",
    "currency",
]

# --- Business rules ---
VALID_TRANSACTION_TYPES = {"CREDIT", "DEBIT"}
VALID_CURRENCY = "USD"
DATE_FORMAT = "%Y-%m-%d"
DATE_STRICT_REGEX = r"^\d{4}-\d{2}-\d{2}$"
AMOUNT_STRICT_REGEX = r"^\d+(\.\d+)?$"

# --- Output file names ---
VALID_OUTPUT_FILE = "valid_transactions.csv"
INVALID_OUTPUT_FILE = "invalid_transactions.csv"
DQ_SUMMARY_FILE = "DQsummary.csv"

# --- Logging ---
LOG_FILE = "pipeline.log"