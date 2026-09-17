# Branch Transaction File Processing Pipeline

A Python/Pandas ETL pipeline that reads daily bank branch transaction files,
validates records against business rules, and produces valid, invalid, and
data-quality summary outputs.

The pipeline also includes logging, reusable validation functions, automated
tests, and handling for file-level and row-level errors.

## How to Run

### 1. Create a Virtual Environment (Optional)

Creating a virtual environment keeps project dependencies isolated.

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

On Mac/Linux:

```bash
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Add Input Files

Place branch transaction CSV files inside the `input/` folder.

Files must follow this naming pattern:

```text
BR<branch_number>_<date>_TRANSACTION.csv
```

Example:

```text
BR001_20260906_TRANSACTION.csv
```

Each file must contain these required columns:

```text
transaction_id
account_id
transaction_date
transaction_type
amount
currency
```

### 4. Run the Pipeline

```bash
python pipeline.py
```

### 5. View the Output

The results are generated inside the `output/` folder:

- `valid_transactions.csv`  
  Records that passed all validation rules.

- `invalid_transactions.csv`  
  Rejected records containing an `error_reason` column. Multiple errors
  for one record are separated by `; `.

- `DQsummary.csv`  
  Data-quality summary containing file-level and row-level metrics.

- `pipeline.log`  
  Execution logs, warnings, errors, and pipeline status information.

The pipeline automatically discovers files matching:

```text
BR*_*_TRANSACTION.csv
```

Adding a new branch file does not require code changes.

## Business Rules Applied

- All six required columns must be present in each file.
- `transaction_id` and `account_id` must not be missing.
- `transaction_date` must follow the `YYYY-MM-DD` format and represent a
  valid calendar date.
- `transaction_type` must be either `CREDIT` or `DEBIT`.
- `amount` must be present, formatted as a plain decimal number, and greater
  than zero.
- `currency` must be `USD`.
- `transaction_id` must be unique across all combined branch files.
- Every occurrence of a duplicated transaction ID is treated as invalid.

## File-Level vs Row-Level Errors

The pipeline distinguishes between file-level errors and row-level errors.

### File-Level Errors

Examples include:

- Missing required columns.
- Unreadable or malformed files.
- No usable branch files available.

Files with schema errors are skipped so that valid files can still be
processed. File-level problems are recorded in the data-quality summary and
pipeline log.

### Row-Level Errors

Examples include:

- Missing `transaction_id`.
- Missing `account_id`.
- Invalid transaction date.
- Invalid transaction type.
- Invalid amount.
- Invalid currency.
- Duplicate transaction ID.

Invalid records are retained in `invalid_transactions.csv` with an
`error_reason` column. When a record violates multiple rules, all applicable
reasons are recorded.

## Project Structure

```text
Banking Data Project/
│
├── input/                          # Input branch transaction CSV files
│
├── output/                         # Generated pipeline outputs
│   ├── valid_transactions.csv
│   ├── invalid_transactions.csv
│   ├── DQsummary.csv
│   └── pipeline.log
│
├── test/                           # Automated pytest tests
│   ├── __init__.py
│   ├── test_validation.py           # Unit tests for validation functions
│   └── test_pipeline.py             # Integration and regression tests
│
├── test_scenarios/                 # Week 2 edge-case scenarios
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
│
├── extract.py                      # File discovery and reading
├── validate.py                     # Data validation rules
├── pipeline.py                     # ETL pipeline orchestration
├── config.py                       # Centralized configuration
├── run_test_scenario.py            # Runs individual test scenarios
│
├── requirements.txt                # Project dependencies
├── Week_2_Test_Results_Template.xlsx
└── README.md                       # Project documentation
```

## Main Components

### `extract.py`

- Discovers matching branch transaction files.
- Reads CSV files as strings to preserve the original input values.
- Checks the required schema.
- Tracks successfully read files, including files with zero data rows.
- Reports file-level errors.

### `validate.py`

- Contains reusable validation functions.
- Validates individual transaction fields.
- Applies validation rules to the combined dataset.
- Records multiple validation errors for the same row.
- Checks duplicate transaction IDs across files.

### `pipeline.py`

- Coordinates the extraction, validation, and loading stages.
- Creates output files.
- Generates data-quality metrics.
- Configures and writes execution logs.
- Handles extraction and processing failures.

### `config.py`

Stores reusable configuration values, including:

- Input and output folder names.
- File-matching pattern.
- Required columns.
- Valid transaction types and currency.
- Date and amount validation patterns.
- Output file names.

## Week 2 Testing and Strengthening

The pipeline was tested against ten edge cases using separate folders under
`test_scenarios/`.

Each scenario contains its own input and output folders, keeping the tests
isolated from the main pipeline folders.

The test results and explanations are recorded in:

```text
Week_2_Test_Results_Template.xlsx
```

### Running a Test Scenario

```bash
python run_test_scenario.py <scenario_folder_name>
```

Example:

```bash
python run_test_scenario.py T01_new_branch
```

Each scenario uses the same pipeline code with a different input and output
folder.

### Week 2 Test Results

| ID | Scenario | Result |
|----|----------|--------|
| T01 | New branch file added | PASS |
| T02 | Header-only file | FAIL → fixed → PASS |
| T03 | Missing required column | PASS |
| T04 | Multiple errors in one transaction | PASS |
| T05 | Cross-file duplicate transaction ID | PASS |
| T06 | Non-numeric or incorrectly formatted amount | FAIL → fixed → PASS |
| T07 | Impossible calendar date | PASS |
| T08 | Different column order | PASS |
| T09 | Pipeline rerun | PASS |
| T10 | Unrelated file in input folder | PASS |

## Week 3 Improvements

The following improvements were added during Week 3:

- Refactored validation logic into reusable functions.
- Added centralized configuration through `config.py`.
- Added unit and integration tests using `pytest`.
- Added pipeline logging with different log levels.
- Added data-quality summary generation.
- Added handling for missing files and rejected files.
- Added tracking of files read, rejected, and processed.
- Added support for recording multiple validation reasons.
- Added test coverage for extraction, validation, integration, and regression.

## Data-Quality Summary

The `DQsummary.csv` file contains information such as:

- Number of files discovered.
- Number of files successfully read.
- Number of rejected files.
- Total input records.
- Valid record count.
- Invalid record count.
- Rejection rate.
- Duplicate transaction count.
- Validation failure counts by rule.
- Per-file row counts.
- File-level error information.

The summary helps identify data-quality issues and provides evidence of
pipeline execution.

## Logging

The pipeline creates:

```text
output/pipeline.log
```

The log records:

- Pipeline start and completion.
- Input and output locations.
- File discovery and extraction status.
- File-level warnings and errors.
- Validation progress.
- Output generation.
- Unexpected failures.

The pipeline also handles situations such as:

- No matching input files.
- All discovered files being rejected.
- One invalid file among valid files.
- Missing or unusable input data.

## Automated Testing

The project uses `pytest` for automated testing.

Run the test suite using:

```bash
py -m pytest -v
```

The tests cover:

- Unit-level validation logic.
- Extraction and validation integration.
- Handling of rejected files.
- Data-quality summary and log generation.
- Regression testing against the original dataset.
- Missing input files and all-files-rejected situations.

The original dataset is expected to produce:

```text
Total records: 24
Valid records: 10
Invalid records: 14
```

## Known Limitations and Future Improvements

- The pipeline currently processes CSV files from a local input directory.
  Future improvements could include cloud storage or database integration.
- Validation rules and configuration values are maintained in Python
  configuration files. A future version could use an external configuration
  file.
- The pipeline currently uses Pandas and is designed for relatively
  manageable file sizes. Large-scale processing could be considered in
  a future implementation.
- Additional monitoring and alerting could be added for repeated file
  failures or abnormal data-quality metrics.

## Reflection

During this project, I developed a better understanding of ETL pipeline design, data validation, error handling, logging, and automated testing. In Week 2, I tested the pipeline using different edge cases, including header-only files, missing columns, invalid amounts, impossible dates, and duplicate transaction IDs. These tests helped me identify problems and improve the pipeline without affecting the expected results of the original dataset.

In Week 3, I focused on making the pipeline more organized, reusable, and easier to maintain. I separated validation logic into reusable functions and centralized configuration values in `config.py`. This helped reduce repeated code and made future changes easier. I also implemented logging to record pipeline execution, file-level errors, warnings, validation progress, and output generation.

Another important learning experience was understanding how to handle errors without stopping the entire pipeline. When one input file contains a schema problem, the pipeline can record the error and continue processing other valid files. I also learned how to generate data-quality summaries containing file-level and row-level metrics, which provide useful information about pipeline performance and data reliability.

I gained practical experience with unit testing, integration testing, and regression testing using `pytest`. Unit tests verify individual validation functions, integration tests check how multiple pipeline components work together, and regression tests ensure that new improvements do not break existing functionality.

Overall, this project improved my problem-solving and debugging skills and helped me understand how reliable data pipelines are designed. In the future, I would like to improve scalability, externalize configuration, add stronger monitoring and alerting, and explore cloud-based data processing solutions.

## Author

Zoya Haider