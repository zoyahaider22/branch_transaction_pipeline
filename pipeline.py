"""
pipeline.py — orchestrates the full Extract -> Transform/Validate -> Load
flow for the branch transaction pipeline.

Run it with:
    python pipeline.py

It expects branch CSV files in ./input/ and writes results to ./output/.
"""

import os
import pandas as pd

from extract import extract_all
from validate import validate_all

INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"


def load_outputs(validated_df, file_errors, output_folder):
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

    # Extra breakdowns beyond the minimum requirement: per-branch counts
    # and a count per distinct error reason. These come almost for free
    # since validate.py already recorded everything we need, and they
    # make the summary genuinely useful to whoever reads it next.
    per_branch = validated_df.groupby("source_file").size()
    for branch_file, count in per_branch.items():
        summary_rows.append({"metric": f"records_from_{branch_file}", "value": count})

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
    combined_df, file_errors = extract_all(input_folder)
    print(f"  -> {len(combined_df)} records read from {combined_df['source_file'].nunique()} file(s).")

    if file_errors:
        print("  File-level errors encountered:")
        for fe in file_errors:
            print(f"    - {fe['file']}: {fe['error']}")

    print("Validating records...")
    validated_df = validate_all(combined_df)

    print(f"Writing outputs to '{output_folder}'...")
    total, valid_count, invalid_count = load_outputs(
        validated_df, file_errors, output_folder
    )

    print("Done.")
    print(f"  Total records:   {total}")
    print(f"  Valid records:   {valid_count}")
    print(f"  Invalid records: {invalid_count}")


if __name__ == "__main__":
    run_pipeline()
