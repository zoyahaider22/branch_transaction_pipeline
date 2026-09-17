"""
test_pipeline.py — integration tests and the regression test for the
pipeline as a whole.

Unlike test_validation.py (one small function, one plain value), these
tests deliberately cross module boundaries — feeding real files through
extract_all() AND validate_all() together, or running the whole
pipeline end to end. That's the definition of an INTEGRATION test:
proving the pieces work correctly TOGETHER, not just individually.
A unit test could pass while an integration test fails, if two
correct pieces are wired together incorrectly — this file is what
would catch that.

Run with:
    pytest test_pipeline.py -v
"""

import os
import pytest
from pathlib import Path

from extract import extract_all
from validate import validate_all
from pipeline import run_pipeline


# ---------------------------------------------------------------------
# Integration tests — real files, multiple stages, temporary folders.
# ---------------------------------------------------------------------
#
# tmp_path is a built-in pytest fixture: pytest automatically creates a
# fresh, empty temporary folder for each test and hands you its path.
# Using it here (instead of pointing at test_scenarios/ or the real
# input/) is deliberate: each test creates exactly the file(s) IT
# needs, with no dependency on what other files or folders happen to
# already exist elsewhere in the project. That makes the test
# self-contained and safe to run in any order, on any machine.

def test_extract_and_validate_together_on_a_small_file(tmp_path):
    """
    One good row and one bad row, through extract_all() then
    validate_all() — proving the two stages hand data to each other
    correctly, not just that each stage works in isolation.
    """
    csv_content = (
        "transaction_id,account_id,transaction_date,transaction_type,amount,currency\n"
        "T9001,A9001,2026-09-06,CREDIT,100.00,USD\n"
        "T9002,A9002,2026-09-06,DEBIT,-5.00,USD\n"
    )
    branch_file = tmp_path / "BR999_20260906_TRANSACTION.csv"
    branch_file.write_text(csv_content)

    combined_df, file_errors, files_read = extract_all(str(tmp_path))
    result_df = validate_all(combined_df)

    assert len(file_errors) == 0
    assert len(result_df) == 2

    valid_row = result_df[result_df["transaction_id"] == "T9001"].iloc[0]
    invalid_row = result_df[result_df["transaction_id"] == "T9002"].iloc[0]

    assert valid_row["is_valid"]
    assert not invalid_row["is_valid"]
    assert "amount" in invalid_row["error_reason"]


def test_a_bad_file_does_not_block_a_good_file(tmp_path):
    """
    Two files in the same folder: one with a missing required column,
    one completely fine. Proves file-level rejection (extract.py) and
    row-level validation (validate.py) work correctly TOGETHER — the
    bad file is skipped and reported, while the good file's data still
    makes it all the way through validation untouched.
    """
    good_csv = (
        "transaction_id,account_id,transaction_date,transaction_type,amount,currency\n"
        "T9101,A9101,2026-09-06,CREDIT,250.00,USD\n"
    )
    bad_csv = (
        "transaction_id,account_id,transaction_date,transaction_type,amount\n"
        "T9201,A9201,2026-09-06,CREDIT,300.00\n"
    )
    (tmp_path / "BR991_20260906_TRANSACTION.csv").write_text(good_csv)
    (tmp_path / "BR992_20260906_TRANSACTION.csv").write_text(bad_csv)

    combined_df, file_errors, files_read = extract_all(str(tmp_path))
    result_df = validate_all(combined_df)

    assert len(file_errors) == 1
    assert "currency" in file_errors[0]["error"]
    assert len(result_df) == 1
    assert result_df.iloc[0]["transaction_id"] == "T9101"
    assert result_df.iloc[0]["is_valid"]


# ---------------------------------------------------------------------
# Regression test — the original 3 files must ALWAYS produce exactly
# 24 total / 10 valid / 14 invalid. If this number ever changes, it
# means a code change altered real, already-verified behavior.
# ---------------------------------------------------------------------

def test_original_data_still_produces_known_results(tmp_path):
    # output_folder is a temporary folder, NOT the real output/ —
    # a test should never overwrite the actual project deliverable
    # just by being run.
    output_folder = str(tmp_path)

    run_pipeline(input_folder="input", output_folder=output_folder)

    with open(os.path.join(output_folder, "valid_transactions.csv")) as f:
        valid_count = sum(1 for _ in f) - 1  # minus 1 for the header row

    with open(os.path.join(output_folder, "invalid_transactions.csv")) as f:
        invalid_count = sum(1 for _ in f) - 1

    assert valid_count == 10
    assert invalid_count == 14
    assert valid_count + invalid_count == 24

def test_pipeline_creates_dq_summary_and_log(tmp_path):
    """
    Verify that a complete pipeline run creates:
    1. valid_transactions.csv
    2. invalid_transactions.csv
    3. DQsummary.csv
    4. pipeline.log

    Also verify that the DQ summary and log contain
    meaningful information.
    """

    # Create a temporary input folder
    input_folder = tmp_path / "input"
    output_folder = tmp_path / "output"

    input_folder.mkdir()

    csv_content = (
        "transaction_id,account_id,transaction_date,"
        "transaction_type,amount,currency\n"
        "T9301,A9301,2026-09-06,CREDIT,100.00,USD\n"
        "T9302,A9302,2026-09-06,DEBIT,-5.00,USD\n"
    )

    branch_file = input_folder / "BR993_20260906_TRANSACTION.csv"
    branch_file.write_text(csv_content)

    # Run the complete pipeline
    run_pipeline(
        input_folder=str(input_folder),
        output_folder=str(output_folder)
    )

    # Check that all expected output files exist
    assert (output_folder / "valid_transactions.csv").exists()
    assert (output_folder / "invalid_transactions.csv").exists()
    assert (output_folder / "DQsummary.csv").exists()
    assert (output_folder / "pipeline.log").exists()

    # Read the DQ summary and verify important metrics
    dq_summary = (output_folder / "DQsummary.csv").read_text()

    assert "total_input_records" in dq_summary
    assert "valid_records" in dq_summary
    assert "invalid_records" in dq_summary
    assert "rejection_rate_percent" in dq_summary

    # Read the log and verify important events
    log_content = (output_folder / "pipeline.log").read_text()

    assert "Pipeline started" in log_content
    assert "Starting extraction" in log_content
    assert "Validation completed" in log_content
    assert "Pipeline completed successfully" in log_content

def test_all_files_rejected_is_logged_and_reported(tmp_path):
    """
    Verify that when all input files have schema errors:

    1. The pipeline raises a clear error.
    2. The error is recorded in pipeline.log.
    3. The pipeline does not continue to validation or output writing.
    """

    input_folder = tmp_path / "input"
    output_folder = tmp_path / "output"

    input_folder.mkdir()

    # This file is missing the required 'currency' column.
    bad_csv = (
        "transaction_id,account_id,transaction_date,"
        "transaction_type,amount\n"
        "T9401,A9401,2026-09-06,CREDIT,100.00\n"
    )

    bad_file = input_folder / "BR994_20260906_TRANSACTION.csv"
    bad_file.write_text(bad_csv)

    # The pipeline should raise ValueError because no file
    # was successfully read.
    with pytest.raises(ValueError, match="No branch files could be read"):
        run_pipeline(
            input_folder=str(input_folder),
            output_folder=str(output_folder)
        )

    # The log should still exist because logging starts
    # before extraction.
    log_file = output_folder / "pipeline.log"

    assert log_file.exists()

    log_content = log_file.read_text()

    assert "Extraction failed" in log_content
    assert "No branch files could be read" in log_content

def test_no_matching_files_is_logged_and_reported(tmp_path):
    """
    Verify that when no branch transaction files are found:

    1. The pipeline raises FileNotFoundError.
    2. The error is recorded in pipeline.log.
    """

    input_folder = tmp_path / "input"
    output_folder = tmp_path / "output"

    input_folder.mkdir()

    # Create files that do not match the branch filename pattern.
    (input_folder / "random_data.csv").write_text(
        "some_column\nsome_value\n"
    )

    (input_folder / "notes.txt").write_text(
        "No branch files available."
    )

    with pytest.raises(
        FileNotFoundError,
        match="No branch transaction files found"
    ):
        run_pipeline(
            input_folder=str(input_folder),
            output_folder=str(output_folder)
        )

    log_file = output_folder / "pipeline.log"

    assert log_file.exists()

    log_content = log_file.read_text()

    assert "Extraction failed" in log_content
    assert "No branch transaction files found" in log_content

def test_multiple_errors_are_preserved_for_one_row(tmp_path):
    """
    Verify that one transaction violating multiple rules
    retains all applicable error reasons.
    """

    csv_content = (
        "transaction_id,account_id,transaction_date,"
        "transaction_type,amount,currency\n"
        "T9501,,2026-02-30,TRANSFER,-10.00,EUR\n"
    )

    branch_file = tmp_path / "BR995_20260906_TRANSACTION.csv"
    branch_file.write_text(csv_content)

    combined_df, file_errors, files_read = extract_all(str(tmp_path))
    result_df = validate_all(combined_df)

    assert len(file_errors) == 0
    assert len(result_df) == 1

    row = result_df.iloc[0]

    assert not row["is_valid"]

    error_reason = row["error_reason"]

    assert "account_id is missing" in error_reason

    assert (
    "transaction_date must be a valid date in YYYY-MM-DD format"
    in error_reason
    )

    assert "transaction_type must be CREDIT or DEBIT" in error_reason

    assert (
    "amount must be present, numeric, and greater than 0"
    in error_reason
    )

    assert "currency must be USD" in error_reason

def test_cross_file_duplicate_ids_are_invalid(tmp_path):
    """
    Verify that duplicate transaction IDs across two branch files
    are detected using the combined dataset.
    """

    csv_header = (
        "transaction_id,account_id,transaction_date,"
        "transaction_type,amount,currency\n"
    )

    file_one = tmp_path / "BR996_20260906_TRANSACTION.csv"
    file_two = tmp_path / "BR997_20260906_TRANSACTION.csv"

    file_one.write_text(
        csv_header +
        "T9601,A9601,2026-09-06,CREDIT,100.00,USD\n"
    )

    file_two.write_text(
        csv_header +
        "T9601,A9602,2026-09-06,DEBIT,200.00,USD\n"
    )

    combined_df, file_errors, files_read = extract_all(str(tmp_path))
    result_df = validate_all(combined_df)

    assert len(file_errors) == 0
    assert len(result_df) == 2

    assert result_df["is_valid"].eq(False).all()

    assert result_df["error_reason"].str.contains(
        "duplicate transaction_id",
        regex=False
    ).all()

    assert set(result_df["source_file"]) == {
        "BR996_20260906_TRANSACTION.csv",
        "BR997_20260906_TRANSACTION.csv",
    } 