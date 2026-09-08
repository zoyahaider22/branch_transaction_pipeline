# Banking Data Project

A Python/Pandas ETL pipeline that reads daily bank branch transaction files,
validates every record against the bank's business rules, and produces
valid/invalid/summary outputs.

## How to run

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Place branch CSV files in the `input/` folder. Files must be named
   following the pattern `BR<branch_number>_<date>_TRANSACTION.csv`
   (e.g. `BR001_20260906_TRANSACTION.csv`) and contain the columns:
   `transaction_id, account_id, transaction_date, transaction_type, amount, currency`.
3. Run:
   ```
   python pipeline.py
   ```
4. Results appear in `output/`:
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

## Project structure

```
Banking Data Project/
├── input/              # branch CSV files go here
├── output/             # generated outputs land here
├── extract.py          # Extract stage: file discovery + reading
├── validate.py         # Transform/Validate stage: one function per rule
├── pipeline.py          # orchestrates extract -> validate -> load
├── requirements.txt
└── README.md
```
## Author

Zoya Haider