"""
validate.py — the "Transform / Validate" stage of the pipeline.

Week 3 refactor: every rule's real logic now lives in a small function
that takes ONE value and returns True/False — e.g. is_valid_amount("ABC")
-> False. The original DataFrame-wide rule_* functions still exist and
are still what pipeline.py actually calls, but they're now thin
wrappers that apply the single-value function across a column with
.apply(), instead of containing the logic themselves.

Why this split matters: a function that takes one plain value and
returns one plain answer is dramatically easier to unit test than one
that needs a whole DataFrame to call — test_validation.py calls these
single-value functions directly, with no DataFrame required at all.
It also means the real logic exists in exactly ONE place: the
DataFrame-wide version can never quietly drift out of sync with what
gets tested, because it delegates to the exact same function.

Each rule function still takes the combined DataFrame and returns a
pandas boolean Series that is True for rows that FAIL that rule, along
with the human-readable reason text for that failure — this part is
unchanged, so validate_all() below still works exactly as before.
"""

import re
from datetime import datetime

import pandas as pd

from config import (
    VALID_TRANSACTION_TYPES,
    VALID_CURRENCY,
    DATE_FORMAT,
    DATE_STRICT_REGEX,
    AMOUNT_STRICT_REGEX,
)


# ---------------------------------------------------------------------
# Single-value functions — the real logic, testable in isolation.
# ---------------------------------------------------------------------

def is_missing_value(value):
    """True if value is null/NaN, or an empty/whitespace-only string."""
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def is_valid_date(value):
    """
    True only if value is a real calendar date in exact YYYY-MM-DD
    format. Two separate checks are needed, not one:
    - The regex enforces the exact SHAPE (4-2-2 digits with dashes),
      because plain datetime parsing is lenient about digit padding —
      Python's own datetime.strptime("2026-9-6", "%Y-%m-%d") happily
      succeeds, even though "2026-9-6" is not actually in YYYY-MM-DD
      format. This is true with or without pandas involved at all.
    - The datetime parse itself catches genuinely impossible dates
      that are correctly shaped but don't exist, like "2026-02-30".
    """
    if is_missing_value(value):
        return False
    value_str = str(value)
    if not re.match(DATE_STRICT_REGEX, value_str):
        return False
    try:
        datetime.strptime(value_str, DATE_FORMAT)
        return True
    except ValueError:
        return False


def is_valid_transaction_type(value):
    return value in VALID_TRANSACTION_TYPES


def is_valid_amount(value):
    """
    True only if value is present, shaped like a plain decimal number,
    and greater than 0. The regex check comes first and rejects
    anything not shaped like a plain number BEFORE trusting a parsed
    value — this is what catches scientific notation like "1e10",
    which Python's own float("1e10") would otherwise happily accept
    as a legitimate positive number.
    """
    if is_missing_value(value):
        return False
    value_str = str(value)
    if not re.match(AMOUNT_STRICT_REGEX, value_str):
        return False
    try:
        numeric_value = float(value_str)
    except (ValueError, TypeError):
        return False
    return numeric_value > 0


def is_valid_currency(value):
    return value == VALID_CURRENCY


# ---------------------------------------------------------------------
# DataFrame-wide rules — thin wrappers that apply the functions above
# across a whole column. These are what pipeline.py actually calls.
# ---------------------------------------------------------------------

def rule_missing_transaction_id(df):
    fails = df["transaction_id"].apply(is_missing_value)
    return fails, "transaction_id is missing"


def rule_missing_account_id(df):
    fails = df["account_id"].apply(is_missing_value)
    return fails, "account_id is missing"


def rule_invalid_date(df):
    fails = ~df["transaction_date"].apply(is_valid_date)
    return fails, "transaction_date must be a valid date in YYYY-MM-DD format"


def rule_invalid_transaction_type(df):
    fails = ~df["transaction_type"].apply(is_valid_transaction_type)
    return fails, "transaction_type must be CREDIT or DEBIT"


def rule_invalid_amount(df):
    fails = ~df["amount"].apply(is_valid_amount)
    return fails, "amount must be present, numeric, and greater than 0"


def rule_invalid_currency(df):
    fails = ~df["currency"].apply(is_valid_currency)
    return fails, "currency must be USD"


def rule_duplicate_transaction_id(df):
    # This rule genuinely cannot be a single-value function — "is this
    # value a duplicate?" is only answerable by looking at every OTHER
    # row too, not one value in isolation. Every occurrence of a
    # transaction_id that appears more than once across the COMBINED
    # dataset is marked invalid — including within a single file, but
    # this is what specifically catches a duplicate that spans two
    # different branch files (e.g. the same ID sent by two branches).
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