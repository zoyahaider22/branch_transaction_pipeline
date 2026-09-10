"""
pipeline.py — orchestrates the full Extract -> Transform/Validate -> Load
flow for the branch transaction pipeline.

See README.md for full setup (virtual environment, installing
dependencies). Once dependencies are installed, run this file with:
    python pipeline.py

It expects branch CSV files in ./input/ and writes results to ./output/.
"""

import os
import pandas as pd

from extract import extract_all
from validate import validate_all

INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"


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

    valid_df.to_csv(os.path.join(output_folder, "valid_transactions.csv"), index=False)
    invalid_df.to_csv(
        os.path.join(output_folder, "invalid_transactions.csv"), index=False
    )

    total = len(validated_df)
    valid_count = len(valid_df)
    invalid_count = len(invalid_df)

    summary_rows = [
        {"metric": "total_input_records", "value": total},
        {"metric": "valid_records", "value": valid_count},
        {"metric": "invalid_records", "value": invalid_count},
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

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(os.path.join(output_folder, "summary.csv"), index=False)

    return total, valid_count, invalid_count


def run_pipeline(input_folder=INPUT_FOLDER, output_folder=OUTPUT_FOLDER):
    print(f"Reading branch files from '{input_folder}'...")
    combined_df, file_errors, files_read = extract_all(input_folder)
    print(f"  -> {len(combined_df)} records read from {len(files_read)} file(s).")

    if file_errors:
        print("  File-level errors encountered:")
        for fe in file_errors:
            print(f"    - {fe['file']}: {fe['error']}")

    print("Validating records...")
    validated_df = validate_all(combined_df)

    print(f"Writing outputs to '{output_folder}'...")
    total, valid_count, invalid_count = load_outputs(
        validated_df, file_errors, files_read, output_folder
    )

    print("Done.")
    print(f"  Total records:   {total}")
    print(f"  Valid records:   {valid_count}")
    print(f"  Invalid records: {invalid_count}")

if __name__ == "__main__":
    run_pipeline()
