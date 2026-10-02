import os
import sys
import pandas as pd

CLEAN_PATH = "data/clean/sales_clean.csv"
REPORT_PATH = "reports/data_quality_report.csv"

REQUIRED_COLS = ["InvoiceNo", "StockCode", "Quantity", "UnitPrice", "InvoiceDate"]
DATE_MIN = pd.Timestamp("2010-12-01")
DATE_MAX = pd.Timestamp("2011-12-09 23:59:59")

# DECISION: thresholds chosen from the Section 1 profile; adjust after reviewing the data
MAX_QTY = 10_000
MAX_PRICE = 1_000


def load_clean():
    return pd.read_csv(
        CLEAN_PATH,
        dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": "Int64"},
        parse_dates=["InvoiceDate"],
    )


# Each rule function returns a boolean Series: True = row is INVALID
RULES = [
    {
        "name": "required_columns_not_null",
        "dimension": "Completeness",
        "severity": "error",
        "check": lambda df: df[REQUIRED_COLS].isna().any(axis=1),
    },
    {
        "name": "quantity_positive",
        "dimension": "Validity",
        "severity": "error",
        "check": lambda df: df["Quantity"] <= 0,
    },
    {
        "name": "unit_price_positive",
        "dimension": "Validity",
        "severity": "error",
        "check": lambda df: df["UnitPrice"] <= 0,
    },
    {
        "name": "invoice_no_six_digits",
        "dimension": "Validity",
        "severity": "error",
        "check": lambda df: ~df["InvoiceNo"].str.match(r"^\d{6}$", na=False),
    },
    {
        "name": "no_duplicate_rows",
        "dimension": "Uniqueness",
        "severity": "error",
        "check": lambda df: df.duplicated(),
    },
    {
        "name": "line_total_consistent",
        "dimension": "Consistency",
        "severity": "error",
        "check": lambda df: (df["LineTotal"] - (df["Quantity"] * df["UnitPrice"]).round(2)).abs() > 0.01,
    },
    {
        "name": "invoice_date_in_range",
        "dimension": "Plausibility",
        "severity": "error",
        "check": lambda df: (df["InvoiceDate"] < DATE_MIN) | (df["InvoiceDate"] > DATE_MAX),
    },
    {
        "name": "country_not_empty",
        "dimension": "Completeness",
        "severity": "error",
        "check": lambda df: df["Country"].isna() | (df["Country"].str.strip() == ""),
    },
    {
        "name": f"quantity_at_most_{MAX_QTY}",
        "dimension": "Plausibility",
        "severity": "warning",
        "check": lambda df: df["Quantity"] > MAX_QTY,
    },
    {
        "name": f"unit_price_at_most_{MAX_PRICE}",
        "dimension": "Plausibility",
        "severity": "warning",
        "check": lambda df: df["UnitPrice"] > MAX_PRICE,
    },
    {
        "name": "stock_code_looks_like_product",
        "dimension": "Validity",
        "severity": "warning",
        "check": lambda df: ~df["StockCode"].str.match(r"^\d{5}[A-Za-z]{0,2}$", na=False),
    },
    {
        "name": "customer_id_present",
        "dimension": "Completeness",
        "severity": "warning",
        "check": lambda df: df["CustomerID"].isna(),
    },
]


def run_rules(df):
    results = []
    for rule in RULES:
        failed = int(rule["check"](df).sum())
        checked = len(df)
        if failed == 0:
            status = "PASS"
        elif rule["severity"] == "error":
            status = "FAIL"
        else:
            status = "WARN"
        results.append({
            "rule_name": rule["name"],
            "dimension": rule["dimension"],
            "severity": rule["severity"],
            "rows_checked": checked,
            "rows_failed": failed,
            "pass_rate": round(100 * (1 - failed / checked), 2),
            "status": status,
        })
    return pd.DataFrame(results)


def main():
    df = load_clean()
    print("Rows validated:", f"{len(df):,}")

    report = run_rules(df)

    print("\n" + "=" * 90)
    print("DATA QUALITY REPORT")
    print("=" * 90)
    print(report.to_string(index=False))

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    report.to_csv(REPORT_PATH, index=False)

    passed = (report["status"] == "PASS").sum()
    warns = (report["status"] == "WARN").sum()
    errors = (report["status"] == "FAIL").sum()
    print(f"\nSummary: {len(report)} rules | {passed} passed | {warns} warnings | {errors} errors")
    print("Report saved to", REPORT_PATH)

    if errors > 0:
        print("VALIDATION FAILED: fix the error-level rules before loading.")
        sys.exit(1)
    print("VALIDATION PASSED.")


if __name__ == "__main__":
    main()