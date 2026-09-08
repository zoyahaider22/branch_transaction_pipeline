"""
validate.py — the "Transform / Validate" stage of the pipeline.

Each business rule is its own small function. A rule function takes
the combined DataFrame and returns a pandas boolean Series that is
True for rows that FAIL that rule, along with the human-readable
reason text for that failure.

Keeping rules as separate functions (rather than one big tangled
if/else block) means:
- every rule can be tested/read in isolation
- adding, removing or tweaking one rule never risks breaking another
- ALL rules run against every row, so a row breaking two rules gets
  both reasons recorded (see combine_errors below)
"""

import pandas as pd

VALID_TRANSACTION_TYPES = {"CREDIT", "DEBIT"}
VALID_CURRENCY = "USD"


def rule_missing_transaction_id(df):
    fails = df["transaction_id"].isna() | (df["transaction_id"].str.strip() == "")
    return fails, "transaction_id is missing"


def rule_missing_account_id(df):
    fails = df["account_id"].isna() | (df["account_id"].str.strip() == "")
    return fails, "account_id is missing"


def rule_invalid_date(df):
    # errors="coerce" turns anything that doesn't parse into a real
    # calendar date (including the impossible "2026-13-06") into NaT.
    parsed = pd.to_datetime(df["transaction_date"], format="%Y-%m-%d", errors="coerce")

    # pd.to_datetime alone is lenient about digit padding — it will
    # happily accept "2026-9-6" as a real date, even though that is
    # NOT actually in YYYY-MM-DD format (month/day must be 2 digits).
    # A regex check enforces the exact shape on top of the date check,
    # so "2026-9-6" is correctly rejected even though it IS a real date.
    strict_format = df["transaction_date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")

    fails = parsed.isna() | ~strict_format
    return fails, "transaction_date must be a valid date in YYYY-MM-DD format"


def rule_invalid_transaction_type(df):
    fails = ~df["transaction_type"].isin(VALID_TRANSACTION_TYPES)
    return fails, "transaction_type must be CREDIT or DEBIT"


def rule_invalid_amount(df):
    # Convert to numeric, forcing anything non-numeric (or blank) to NaN.
    numeric_amount = pd.to_numeric(df["amount"], errors="coerce")
    fails = numeric_amount.isna() | (numeric_amount <= 0)
    return fails, "amount must be present, numeric, and greater than 0"


def rule_invalid_currency(df):
    fails = df["currency"] != VALID_CURRENCY
    return fails, "currency must be USD"


def rule_duplicate_transaction_id(df):
    # Every occurrence of a transaction_id that appears more than once
    # across the COMBINED dataset is marked invalid — including within
    # a single file, but this is what specifically catches a duplicate
    # that spans two different branch files (e.g. the same ID sent by
    # two branches).
    counts = df["transaction_id"].value_counts()
    duplicated_ids = counts[counts > 1].index
    fails = df["transaction_id"].isin(duplicated_ids)
    return fails, "duplicate transaction_id across combined branch data"


# Rules that need the transaction_id itself to already be present to make
# sense (date/type/amount/currency/duplicate checks on a blank ID row would
# be noise) are still run on every row regardless — an empty transaction_id
# row can still meaningfully fail "account_id is missing" too, for example.
ALL_RULES = [
    rule_missing_transaction_id,
    rule_missing_account_id,
    rule_invalid_date,
    rule_invalid_transaction_type,
    rule_invalid_amount,
    rule_invalid_currency,
    rule_duplicate_transaction_id,
]


def validate_all(df):
    """
    Run every rule against every row and return the same DataFrame with
    two new columns:
      - is_valid: True/False
      - error_reason: "; "-joined list of every rule this row broke
                       (empty string for valid rows)

    Running every rule independently (instead of stopping at the first
    failure) is what allows a row like T2008 — missing account_id AND
    an invalid transaction_type — to end up with BOTH reasons recorded.
    """
    df = df.copy()
    reasons_per_row = [[] for _ in range(len(df))]

    for rule_func in ALL_RULES:
        fails, reason_text = rule_func(df)
        for idx in df.index[fails]:
            reasons_per_row[df.index.get_loc(idx)].append(reason_text)

    df["error_reason"] = ["; ".join(reasons) for reasons in reasons_per_row]
    df["is_valid"] = df["error_reason"] == ""

    return df