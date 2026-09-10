# Branch Transaction File Processing Pipeline

A Python/Pandas ETL pipeline that reads daily bank branch transaction files,
validates every record against the bank's business rules, and produces
valid/invalid/summary outputs.

## How to run

1. (Optional but recommended) Create and activate a virtual environment,
   so this project's dependencies stay isolated from other Python projects
   on your machine:
   ```
   python -m venv .venv
   ```
   Activate it — on Windows PowerShell:
   ```
   .venv\Scripts\Activate.ps1
   ```
   On Mac/Linux:
   ```
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Place branch CSV files in the `input/` folder. Files must be named
   following the pattern `BR<branch_number>_<date>_TRANSACTION.csv`
   (e.g. `BR001_20260906_TRANSACTION.csv`) and contain the columns:
   `transaction_id, account_id, transaction_date, transaction_type, amount, currency`.
4. Run:
   ```
   python pipeline.py
   ```
5. Results appear in `output/`:
   - `valid_transactions.csv` — records that passed every rule.
   - `invalid_transactions.csv` — rejected records with an `error_reason`
     column (multiple reasons for one row are separated by `; `).
   - `summary.csv` — total/valid/invalid record counts, plus a per-branch
     breakdown and a count of how many records failed each specific rule.

The pipeline automatically picks up any file in `input/` matching the
`BR*_*_TRANSACTION.csv` pattern — adding a new branch file requires no
code changes.

## Business rules applied

- All 6 required columns must be present in each file.
- `transaction_id` and `account_id` must not be missing.
- `transaction_date` must be a valid date in `YYYY-MM-DD` format.
- `transaction_type` must be `CREDIT` or `DEBIT`.
- `amount` must be present, numeric, and greater than 0.
- `currency` must be `USD`.
- `transaction_id` must be unique across all branch files combined; every
  occurrence of a duplicated ID is treated as invalid.

## File-level vs Row-level Errors

The pipeline distinguishes between file-level/schema errors and
row-level validation errors.

File-level errors:
- Missing required columns
- The affected file is skipped and the error is reported in the
  pipeline summary.

Row-level errors:
- Missing transaction_id
- Missing account_id
- Invalid transaction_date
- Invalid transaction_type
- Invalid amount
- Invalid currency
- Duplicate transaction_id

Row-level errors are retained in invalid_transactions.csv with
their corresponding error_reason. 

## Project structure

```
Banking Data Project/
├── input/                  # branch CSV files go here
├── output/                 # generated outputs land here
├── test_scenarios/         # Week 2 extension: isolated edge-case tests (see below)
│   ├── T01_new_branch/
│   ├── T02_header_only/
│   ├── T03_missing_column/
│   ├── T04_multiple_errors/
│   ├── T05_cross_file_duplicate/
│   ├── T06_non_numeric_amount/
│   ├── T07_impossible_date/
│   ├── T08_different_column_order/
│   ├── T09_rerun/
│   └── T10_unexpected_file/
├── extract.py               # Extract stage: file discovery + reading
├── validate.py               # Transform/Validate stage: one function per rule
├── pipeline.py                # orchestrates extract -> validate -> load
├── run_test_scenario.py       # runs the pipeline against one test_scenarios/ folder
├── requirements.txt
├── Week_2_Test_Results_Template.xlsx   # filled-in test results and reflection
└── README.md
```

## Week 2 Extension: Testing & Strengthening the Pipeline

This extension stress-tests the pipeline above against 10 edge cases it
hadn't been checked against before, to see whether it holds up under
input that isn't clean — not just whether it runs on the original 3
sample files.

Each test lives in its own folder under `test_scenarios/`, with its own
`input/` and `output/`, completely isolated from the real pipeline's
`input/`/`output/` above. Full results, expected vs. actual behavior,
and reasoning for every test are recorded in
`Week_2_Test_Results_Template.xlsx`.

### Running a test scenario

```
python run_test_scenario.py <scenario_folder_name>
```

For example:
```
python run_test_scenario.py T01_new_branch
```

This calls the exact same `pipeline.py` used for real data — no
separate test-only code path — just pointed at a different
input/output folder pair, so a test scenario can never affect or be
affected by the real deliverable in `input/`/`output/`.

### What was tested

| ID | Scenario | Result |
|---|---|---|
| T01 | New branch file added | PASS |
| T02 | Header-only file (valid headers, zero data rows) | FAIL → fixed → PASS |
| T03 | File missing a required column entirely | PASS |
| T04 | One transaction breaking multiple rules at once | PASS |
| T05 | Same transaction_id duplicated across two branch files | PASS |
| T06 | Non-numeric / oddly-formatted amount values | FAIL → fixed → PASS |
| T07 | Dates that are correctly formatted but calendar-impossible | PASS |
| T08 | Same columns, different order in the file | PASS |
| T09 | Running the pipeline twice on identical input | PASS |
| T10 | Unrelated files sitting in the input folder | PASS |

### Bugs found and fixed

**1. Empty branch files were invisible in reporting (T02).**
A file with valid headers but zero data rows was processed without
crashing, but `summary.csv` had no record that the file existed at
all — making a branch that genuinely sent zero transactions
indistinguishable from a branch whose file never arrived. Fixed by
tracking every successfully-read file (with its row count, including
0) in `extract_all()`, and using that list — instead of grouping the
data itself — to build the per-branch summary in `pipeline.py`.

**2. Scientific notation was accepted as a valid amount (T06).**
`pd.to_numeric()` parses a value like `"1e10"` as a legitimate
positive number, even though no real transaction amount is ever
written that way. Fixed by adding a regex check in
`rule_invalid_amount()` (`validate.py`) requiring the raw value to be
shaped like a plain decimal number before trusting the parsed result.

Both fixes were verified against the original 3-branch dataset
afterward to confirm the real pipeline's output (24 total / 10 valid /
14 invalid records) was unaffected.

## Author

Zoya Haider