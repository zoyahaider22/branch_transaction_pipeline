"""
test_validation.py — unit tests for the single-value functions in
validate.py (is_valid_amount, is_valid_date, is_valid_currency,
is_valid_transaction_type, is_missing_value).

These are UNIT tests specifically because each one calls exactly one
small function with one plain value and checks one plain answer — no
DataFrame, no file, no pipeline involved. That isolation is the whole
point: if test_valid_amount_rejects_scientific_notation fails, you
know with certainty the bug is inside is_valid_amount() itself, not
somewhere else in the pipeline.

Run with:
    pytest test_validation.py -v
or, to run every test file in the project at once:
    pytest -v
"""

from validate import (
    is_missing_value,
    is_valid_date,
    is_valid_transaction_type,
    is_valid_amount,
    is_valid_currency,
)


# ---------------------------------------------------------------------
# is_valid_amount — 4 tests
# ---------------------------------------------------------------------

def test_valid_amount_accepts_a_normal_positive_number():
    assert is_valid_amount("300.00") is True


def test_valid_amount_rejects_non_numeric_text():
    # The original, simplest case the assignment names explicitly.
    assert is_valid_amount("ABC") is False


def test_valid_amount_rejects_negative_and_zero():
    assert is_valid_amount("-50.00") is False
    assert is_valid_amount("0.00") is False


def test_valid_amount_rejects_scientific_notation():
    # Regression-style: this is the exact real bug found during the
    # Week 2 extension (T06). float("1e10") parses fine as a number,
    # so without the regex check this would wrongly return True.
    assert is_valid_amount("1e10") is False


# ---------------------------------------------------------------------
# is_valid_date — 4 tests
# ---------------------------------------------------------------------

def test_valid_date_accepts_a_correctly_formatted_real_date():
    assert is_valid_date("2026-09-06") is True


def test_valid_date_rejects_an_impossible_calendar_date():
    # February never has 30 days, no matter how correct the FORMAT is.
    assert is_valid_date("2026-02-30") is False


def test_valid_date_rejects_non_zero_padded_dates():
    # Regression-style: the exact real bug found comparing against a
    # classmate's project. datetime.strptime alone would accept this.
    assert is_valid_date("2026-9-6") is False


def test_valid_date_rejects_wrong_separator():
    assert is_valid_date("2026/09/06") is False


# ---------------------------------------------------------------------
# is_valid_currency and is_valid_transaction_type — 4 tests
# ---------------------------------------------------------------------

def test_valid_currency_accepts_usd():
    assert is_valid_currency("USD") is True


def test_valid_currency_rejects_other_currencies():
    assert is_valid_currency("EUR") is False
    assert is_valid_currency("GBP") is False


def test_valid_transaction_type_accepts_credit_and_debit():
    assert is_valid_transaction_type("CREDIT") is True
    assert is_valid_transaction_type("DEBIT") is True


def test_valid_transaction_type_rejects_anything_else():
    assert is_valid_transaction_type("TRANSFER") is False
    assert is_valid_transaction_type("PIZZA") is False


# ---------------------------------------------------------------------
# is_missing_value — 3 tests
# ---------------------------------------------------------------------

def test_missing_value_detects_blank_string():
    assert is_missing_value("") is True


def test_missing_value_detects_whitespace_only_string():
    assert is_missing_value("   ") is True


def test_missing_value_accepts_a_real_value_as_not_missing():
    assert is_missing_value("A1001") is False