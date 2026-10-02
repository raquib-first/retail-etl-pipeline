# Retail Transaction ETL & Data Quality Pipeline

An end-to-end data pipeline that takes a raw, messy retail transaction file and turns it into a validated, queryable SQLite database with SQL reports. Built in Python (pandas) and SQL.

**Pipeline:** Profile -> Clean -> Validate -> Load -> Report

| Stage | Script | What it does |
|---|---|---|
| 1. Profile | `src/01_profile.py` | Measures the raw data: types, nulls, duplicates, ranges, cancellations |
| 2. Clean (Transform) | `src/02_clean.py` | Fixes types, removes duplicates, splits cancellations, rejects invalid rows, adds derived columns |
| 3. Validate | `src/03_validate.py` | Runs 12 data-quality rules and writes a pass/fail report |
| 4. Load | `src/04_load.py` | Loads validated data into a normalized SQLite database and verifies it |
| 5. Report | `src/05_run_reports.py` | Runs the SQL reports in `sql/` and saves results as CSV |

## Dataset

[UCI Online Retail dataset](https://archive.ics.uci.edu/dataset/352/online+retail): 541,909 line items from a UK online retailer, 2010-12-01 to 2011-12-09, with 8 columns (InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country).

The data is not included in this repo. Download it, convert it to CSV, and save it as `data/raw_data/Online_Retail.csv`.

## Findings from profiling the raw data

| Check | Result |
|---|---|
| Rows / columns | 541,909 / 8 |
| Missing `CustomerID` | 135,080 rows (24.93%) |
| Missing `Description` | 1,454 rows (0.27%) |
| Fully duplicated rows | 5,268 (0.97%) |
| Negative `Quantity` | 10,624 rows |
| `UnitPrice` <= 0 | 2,517 rows |
| Invoices starting with "C" (cancellations) | 9,288 rows |
| `InvoiceDate` stored as | text (converted to datetime in cleaning) |

## Cleaning and reconciliation

Rows are never silently deleted. Every raw row ends up in exactly one group, and the script checks that the groups add up to the raw count.

| Group | Rows |
|---|---|
| Raw rows | 541,909 |
| Duplicates removed | 5,268 |
| Cancellations (saved separately) | 9,251 |
| Rejected (saved with a reason) | 2,513 |
| **Clean** | **524,877** |

Rejected rows: 1,454 with a missing description, and the remaining 1,059 with a price of zero or less or an invalid invoice number format. Each rejected row carries a `reject_reason` in `data/clean/rejected.csv`.

Of the 10,624 negative-quantity rows in the raw data, 9,288 were "C" invoices (cancellations). The other 1,336 all had either no description or a zero price, which fits stock adjustments or write-offs, and they were rejected rather than treated as sales.

## Data-quality rules

`src/03_validate.py` checks the clean data against 12 rules. Error-level rules stop the run with a non-zero exit code; warnings are reported but allowed.

| Rule | Dimension | Severity | Rows failed |
|---|---|---|---|
| Required columns not null | Completeness | error | 0 |
| Quantity > 0 | Validity | error | 0 |
| UnitPrice > 0 | Validity | error | 0 |
| InvoiceNo is six digits | Validity | error | 0 |
| No duplicate rows | Uniqueness | error | 0 |
| LineTotal = Quantity x UnitPrice | Consistency | error | 0 |
| InvoiceDate within 2010-12-01 to 2011-12-09 | Plausibility | error | 0 |
| Country not empty | Completeness | error | 0 |
| Quantity <= 10,000 | Plausibility | warning | 2 |
| UnitPrice <= 1,000 | Plausibility | warning | 53 |
| StockCode looks like a product code | Validity | warning | 2,373 |
| CustomerID present | Completeness | warning | 132,185 |

The first validation run failed on one row with a malformed invoice number that cleaning had missed. The fix went into the cleaning step (a new reject rule), not into a looser validation rule, and the second run passed with 0 errors.

## Database schema

SQLite database (`data/retail.db`), created by `sql/schema.sql`:

```
customers (customer_id PK)
products (stock_code PK, description, is_product)
invoices (invoice_no PK, invoice_date, customer_id FK NULL, country)
invoice_items (item_id PK, invoice_no FK, stock_code FK, quantity, unit_price, line_total)
cancellation_items (item_id PK, invoice_no, invoice_date, customer_id, stock_code, quantity, unit_price, line_total)
```

Row counts after loading: 4,338 customers, 3,921 products, 19,959 invoices, 524,877 invoice items, 9,251 cancellation items. The loader checks that these match the source CSV files, that total `line_total` matches (10,631,048.74), and that there are 0 foreign key violations.

## Design decisions

- **Rows with no `CustomerID` are kept** (about 25% of sales). They are real sales, so `invoices.customer_id` allows NULL instead of dropping them.
- **Cancellations live in their own table with no foreign keys**, because many refer to sales outside the date range.
- **Invoices with several timestamps keep the earliest one.** 42 invoices had line items stamped up to one minute apart.
- **Stock codes with several descriptions keep the most frequent one.**
- **`is_product = 0` for 13 codes** (postage, bank charges, Amazon fee, carriage, samples, manual entries, and gift vouchers), identified by an explicit list. A code-pattern rule was tried first but wrongly flagged real products such as the `DCGS...` series.
- **Database constraints repeat the validation rules** (`CHECK quantity > 0`, `CHECK unit_price > 0`), so bad data is rejected even if the pipeline is bypassed.

## SQL reports

Run with `python src/05_run_reports.py`. Results are saved to `reports/`.

| File | Report |
|---|---|
| `01_revenue_by_month.sql` | Gross revenue, invoice count and average order value per month |
| `02_top_products.sql` | Top 10 products by gross revenue (excludes non-products) |
| `03_top_customers.sql` | Top 10 customers by gross revenue (excludes missing customers) |
| `04_revenue_by_country.sql` | Revenue, customers and share of total by country |
| `05_cancellation_rate.sql` | Normal vs cancelled invoices per month |
| `06_net_revenue_by_month.sql` | Gross sales, cancellations and net revenue per month |
| `07_top_products_net.sql` | Top 10 products by net revenue |

### Key results

- **Gross revenue: 10,631,048.74. Cancellations: 893,979.73 (about 8.4% of gross). Net revenue: about 9,737,069.**
- **Gross reports were distorted by large cancelled orders.** One product showed 80,995 units sold, the exact mirror of a cancelled quantity, and it disappears from the top 10 once cancellations are subtracted. The net reports are the more reliable view.
- **Revenue peaks in November 2011** (net 1,456,146), consistent with seasonal gift buying.
- **The UK accounts for 84.57% of revenue.** The Netherlands, Ireland (EIRE), Germany and France follow at about 2-3% each.
- **13.7% to 19.3% of invoices each month are cancelled.**

### Limitations

- December 2011 is a partial month (the data ends on 9 December), so its figures are not comparable to full months.
- Cancellations are dated when they were made, not when the original sale happened, so a month's net figure can include refunds for earlier sales.
- Product net revenue joins on the `products` table, which is built from clean sales only. Cancelled codes that never appear in sales are dropped from that report.
- Hong Kong rows have no `CustomerID`, so its customer count is 0. "Unspecified" and "European Community" appear as country values in the source data.
- No dashboard is included yet; reports are SQL queries with CSV output.

## How to run

```
python -m venv venv
venv\Scripts\activate
pip install pandas openpyxl

python src\02_clean.py
python src\03_validate.py
python src\04_load.py
python src\05_run_reports.py
```

`src/01_profile.py` is optional and prints the raw-data profile. All scripts run from the project root, and `04_load.py` deletes and rebuilds `data/retail.db` each time, so every stage can be re-run safely.

## Project structure

```
retail-etl-pipeline/
├── data/
│   ├── raw_data/     # original file (not in repo)
│   └── clean/        # sales_clean.csv, cancellations.csv, rejected.csv
├── sql/              # schema.sql and the 7 report queries
├── src/              # pipeline scripts
├── reports/          # data_quality_report.csv and report outputs
└── README.md
```

## Tech

Python 3, pandas, SQLite, SQL (JOINs, CTEs, aggregations, subqueries), Git.
