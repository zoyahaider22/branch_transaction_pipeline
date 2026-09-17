"""
extract.py — the "Extract" stage of the pipeline.

Responsible for exactly two things:
1. Finding every branch transaction file in the input folder (without
   hardcoding file names, so new branches "just work").
2. Reading them all in and stacking them into one combined DataFrame,
   checking that each file actually has the columns we expect.

Nothing in here judges whether a transaction_id or amount is *valid* —
that is validate.py's job. This file only answers "can we read this
data at all, and does it have the shape we expect?"
"""

import glob
import os
import pandas as pd

from config import REQUIRED_COLUMNS, BRANCH_FILE_PATTERN

def find_branch_files(input_folder):
    """
    Return a sorted list of file paths matching the branch file naming
    pattern: BR<digits>_<date>_TRANSACTION.csv

    Using a pattern instead of a fixed list of filenames is what lets
    the pipeline handle BR004, BR005, ... without any code changes.
    """
    pattern = os.path.join(input_folder, BRANCH_FILE_PATTERN)
    files = sorted(glob.glob(pattern))
    return files


def read_branch_file(file_path):
    """
    Read a single branch CSV and check it has all required columns.

    Returns a tuple: (dataframe_or_None, column_error_or_None)

    If a required column is missing entirely, we do NOT try to process
    the file row by row — a missing column is a structural/pipeline
    problem, not a row-level data-quality problem, so it's reported
    separately and clearly instead of silently treating missing
    columns as blank values.
    """
    try:
        df = pd.read_csv(file_path, dtype=str)  # read everything as text first;
        # we convert types deliberately during validation instead of letting
        # pandas guess, so we stay in control of what counts as "invalid".
    except Exception as e:
        return None, f"Could not read file: {e}"

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        return None, f"Missing required column(s): {', '.join(missing_columns)}"

    df["source_file"] = os.path.basename(file_path)
    return df, None


def extract_all(input_folder):
    """
    Find and read every branch file, combining the valid ones into a
    single DataFrame. Also returns:
    - file_errors: any file-level errors (missing columns, unreadable file)
    - files_read: every file successfully read, WITH its row count,
      even if that count is 0.

    files_read exists specifically because a header-only file (valid
    structure, zero data rows) contributes nothing to the combined
    DataFrame's row-based statistics — a plain groupby("source_file")
    would make that file invisible in reporting, indistinguishable from
    a file that was never sent at all. Tracking it here means a branch
    that genuinely sent zero transactions is still visible and
    accounted for, which matters in a real pipeline: an empty file and
    a missing file are different situations and should be reported
    differently.
    """
    files = find_branch_files(input_folder)

    if not files:
        raise FileNotFoundError(
            f"No branch transaction files found in '{input_folder}'. "
            f"Expected files matching pattern {BRANCH_FILE_PATTERN}"
        )

    all_dataframes = []
    file_errors = []
    files_read = []

    for file_path in files:
        df, error = read_branch_file(file_path)
        if error:
            file_errors.append({"file": os.path.basename(file_path), "error": error})
            continue
        all_dataframes.append(df)
        files_read.append({"file": os.path.basename(file_path), "row_count": len(df)})

    if not all_dataframes:
        raise ValueError(
            "No branch files could be read successfully. See file_errors for details."
        )

    combined = pd.concat(all_dataframes, ignore_index=True)
    return combined, file_errors, files_read