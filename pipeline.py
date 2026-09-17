"""
pipeline.py — orchestrates the full Extract -> Transform/Validate -> Load
flow for the branch transaction pipeline.

See README.md for full setup (virtual environment, installing
dependencies). Once dependencies are installed, run this file with:
    python pipeline.py

It expects branch CSV files in ./input/ and writes results to ./output/.
"""

import os
import logging
import pandas as pd

from extract import extract_all
from validate import validate_all
from config import (
    INPUT_FOLDER,
    OUTPUT_FOLDER,
    VALID_OUTPUT_FILE,
    INVALID_OUTPUT_FILE,
    DQ_SUMMARY_FILE,
    LOG_FILE,
)

def setup_logger(output_folder):
    """
    Create a logger that writes pipeline events to pipeline.log.

    Each pipeline run gets its own log file inside the selected
    output folder.
    """
    os.makedirs(output_folder, exist_ok=True)

    logger = logging.getLogger("branch_transaction_pipeline")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove handlers from previous runs.
    # This prevents duplicate log messages during testing.
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    log_path = os.path.join(output_folder, LOG_FILE)

    file_handler = logging.FileHandler(
        log_path,
        mode="w",
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def load_outputs(validated_df, file_errors, files_read, output_folder):
    """
    The "Load" stage: write the three required output files.
    Re-running the pipeline simply overwrites these each time, so no
    manual cleanup is ever needed between runs.
    """
    os.makedirs(output_folder, exist_ok=True)

    valid_df = validated_df[validated_df["is_valid"]].drop(
        columns=["is_valid", "error_reason"]
    )
    invalid_df = validated_df[~validated_df["is_valid"]].drop(columns=["is_valid"])

    valid_df.to_csv(os.path.join(output_folder, VALID_OUTPUT_FILE), index=False)
    invalid_df.to_csv(os.path.join(output_folder, INVALID_OUTPUT_FILE), index=False)

    total = len(validated_df)
    valid_count = len(valid_df)
    invalid_count = len(invalid_df)
    rejection_rate = round((invalid_count / total * 100), 2) if total > 0 else 0.0

    # Duplicate count pulled out as its own explicit metric, not just
    # buried inside the per-reason breakdown further down 
    duplicate_count = 0
    if invalid_count > 0:
        duplicate_count = int(
            invalid_df["error_reason"]
            .str.contains("duplicate transaction_id", regex=False)
            .sum()
        )

    files_discovered = len(files_read) + len(file_errors)

    summary_rows = [
        {"metric": "files_discovered", "value": files_discovered},
        {"metric": "files_successfully_read", "value": len(files_read)},
        {"metric": "files_rejected_or_skipped", "value": len(file_errors)},
        {"metric": "total_input_records", "value": total},
        {"metric": "valid_records", "value": valid_count},
        {"metric": "invalid_records", "value": invalid_count},
        {"metric": "rejection_rate_percent", "value": rejection_rate},
        {"metric": "duplicate_transaction_count", "value": duplicate_count},
    ]
    # Per-branch counts come from files_read (every file successfully
    # opened), NOT from grouping the data itself. A header-only file
    # contributes 0 rows and would be completely invisible to a
    # groupby — using files_read means a branch that genuinely sent
    # zero transactions still shows up here, explicitly, as 0 — instead
    # of looking identical to a branch whose file never arrived at all.
    for entry in files_read:
        summary_rows.append(
            {"metric": f"records_from_{entry['file']}", "value": entry["row_count"]}
        )

    if invalid_count > 0:
        reason_counts = (
            invalid_df["error_reason"]
            .str.split("; ")
            .explode()
            .value_counts()
        )
        for reason, count in reason_counts.items():
            summary_rows.append({"metric": f"invalid_reason: {reason}", "value": count})

    if file_errors:
        for fe in file_errors:
            summary_rows.append(
                {"metric": f"file_error: {fe['file']}", "value": fe["error"]}
            )

    summary_df = pd.DataFrame(summary_rows, dtype=object)
    summary_df.to_csv(os.path.join(output_folder, DQ_SUMMARY_FILE), index=False)

    return total, valid_count, invalid_count


def run_pipeline(input_folder=INPUT_FOLDER, output_folder=OUTPUT_FOLDER):
    os.makedirs(output_folder, exist_ok=True)

    logger = setup_logger(output_folder)

    logger.info("Pipeline started.")
    logger.info(f"Input folder: {input_folder}")
    logger.info(f"Output folder: {output_folder}")

    print(f"Reading branch files from '{input_folder}'...")
    logger.info("Starting extraction.")

    try:
        combined_df, file_errors, files_read = extract_all(input_folder)
    except Exception as error:
        logger.error(f"Extraction failed: {error}")
        raise

    logger.info(
        f"Extraction completed: {len(combined_df)} records "
        f"read from {len(files_read)} file(s)."
    )

    print(
        f"  -> {len(combined_df)} records read "
        f"from {len(files_read)} file(s)."
    )

    if file_errors:
        print("  File-level errors encountered:")
        logger.warning(
            f"{len(file_errors)} file-level error(s) encountered."
        )

        for fe in file_errors:
            print(f"    - {fe['file']}: {fe['error']}")

            logger.warning(
                f"File rejected: {fe['file']} - {fe['error']}"
            )

    print("Validating records...")
    logger.info("Starting validation.")

    validated_df = validate_all(combined_df)

    logger.info("Validation completed.")

    print(f"Writing outputs to '{output_folder}'...")
    logger.info("Starting output writing.")

    total, valid_count, invalid_count = load_outputs(
        validated_df,
        file_errors,
        files_read,
        output_folder
    )

    logger.info("Output files written successfully.")

    print("Done.")
    print(f"  Total records:   {total}")
    print(f"  Valid records:   {valid_count}")
    print(f"  Invalid records: {invalid_count}")

    logger.info(
        f"Pipeline completed successfully. "
        f"Total: {total}, Valid: {valid_count}, "
        f"Invalid: {invalid_count}"
    )
    
if __name__ == "__main__":
    run_pipeline()
