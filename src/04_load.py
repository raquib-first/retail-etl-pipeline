import os
import sqlite3
import pandas as pd

CLEAN_PATH = "data/clean/sales_clean.csv"
CANCEL_PATH = "data/clean/cancellations.csv"
DB_PATH = "data/retail.db"
SCHEMA_PATH = "sql/schema.sql"

# DECISION: codes that are fees, postage, samples, manual entries or vouchers, not products.
# Compared in upper case, so "M" and "m" are both caught; "GIFT_" vouchers are matched by prefix.
NON_PRODUCT_CODES = {"AMAZONFEE", "BANK CHARGES", "C2", "DOT", "M", "POST", "S"}


def read_csv(path):
    return pd.read_csv(
        path,
        dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": "Int64"},
        parse_dates=["InvoiceDate"],
    )


def nulls_to_none(series):
    # nullable Int64 -> Python ints with real None, so SQLite stores NULL
    return series.astype(object).where(series.notna(), None)


def check_invoice_consistency(df):
    # customer and country must be the same within an invoice
    counts = df.groupby("InvoiceNo")[["CustomerID", "Country"]].nunique(dropna=False)
    if (counts.max() > 1).any():
        raise ValueError("Invoices with conflicting customer or country.")

    # dates may differ slightly within an invoice; only fail if the gap is large
    g = df.groupby("InvoiceNo")["InvoiceDate"].agg(["min", "max"])
    gaps = g["max"] - g["min"]
    print("Invoices with more than one date:", int((gaps > pd.Timedelta(0)).sum()))
    print("Max date gap within an invoice:", gaps.max())
    # DECISION: tolerate gaps up to 1 hour
    if gaps.max() > pd.Timedelta(hours=1):
        raise ValueError("Invoice date gap is larger than expected.")


# ---------- BUILD TABLES IN PANDAS ----------
def build_customers(df):
    ids = df["CustomerID"].dropna().astype("int64").drop_duplicates()
    return pd.DataFrame({"customer_id": ids})


def build_products(df):
    # DECISION: if a stock code has several descriptions, keep the most frequent one
    desc = df.groupby("StockCode")["Description"].agg(lambda s: s.mode().iloc[0])
    products = desc.reset_index()
    products.columns = ["stock_code", "description"]

    codes = products["stock_code"].str.upper()
    is_non_product = codes.isin(NON_PRODUCT_CODES) | codes.str.startswith("GIFT_")
    products["is_product"] = (~is_non_product).astype(int)
    return products


def build_invoices(df):
    # DECISION: one date per invoice = the earliest line-item timestamp
    inv = (
        df.groupby("InvoiceNo", as_index=False)
          .agg(InvoiceDate=("InvoiceDate", "min"),
               CustomerID=("CustomerID", "first"),
               Country=("Country", "first"))
    )
    inv.columns = ["invoice_no", "invoice_date", "customer_id", "country"]
    inv["invoice_date"] = inv["invoice_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    inv["customer_id"] = nulls_to_none(inv["customer_id"])
    return inv


def build_items(df):
    items = df[["InvoiceNo", "StockCode", "Quantity", "UnitPrice", "LineTotal"]].copy()
    items.columns = ["invoice_no", "stock_code", "quantity", "unit_price", "line_total"]
    return items


def build_cancellations(df):
    c = df[["InvoiceNo", "InvoiceDate", "CustomerID", "StockCode", "Quantity", "UnitPrice", "LineTotal"]].copy()
    c.columns = ["invoice_no", "invoice_date", "customer_id", "stock_code", "quantity", "unit_price", "line_total"]
    c["invoice_date"] = c["invoice_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    c["customer_id"] = nulls_to_none(c["customer_id"])
    return c


# ---------- DATABASE ----------
def create_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # fresh start, so the script is safe to re-run
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def insert(conn, df, table):
    df.to_sql(table, conn, if_exists="append", index=False, chunksize=50_000)
    print(f"Loaded {len(df):>9,} rows into {table}")


# ---------- VERIFY ----------
def scalar(conn, sql):
    return conn.execute(sql).fetchone()[0]


def verify(conn, clean, cancellations, customers, products, invoices):
    print("\n" + "=" * 50)
    print("VERIFICATION")
    print("=" * 50)

    checks = [
        ("invoice_items rows", scalar(conn, "SELECT COUNT(*) FROM invoice_items"), len(clean)),
        ("cancellation_items rows", scalar(conn, "SELECT COUNT(*) FROM cancellation_items"), len(cancellations)),
        ("customers rows", scalar(conn, "SELECT COUNT(*) FROM customers"), len(customers)),
        ("products rows", scalar(conn, "SELECT COUNT(*) FROM products"), len(products)),
        ("invoices rows", scalar(conn, "SELECT COUNT(*) FROM invoices"), len(invoices)),
        ("sum of line_total", round(scalar(conn, "SELECT SUM(line_total) FROM invoice_items"), 2),
         round(clean["LineTotal"].sum(), 2)),
    ]
    all_ok = True
    for name, db_val, expected in checks:
        ok = db_val == expected
        all_ok &= ok
        print(f"{name:<26} db={db_val:>14,} expected={expected:>14,}  {'OK' if ok else 'MISMATCH'}")

    fk_problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    print("Foreign key violations:", len(fk_problems))
    all_ok &= len(fk_problems) == 0

    split = conn.execute(
        "SELECT is_product, COUNT(*) FROM products GROUP BY is_product ORDER BY is_product"
    ).fetchall()
    print("products by is_product (0 = non-product, 1 = product):", split)

    if not all_ok:
        raise SystemExit("VERIFICATION FAILED")
    print("\nAll checks passed.")


def main():
    clean = read_csv(CLEAN_PATH)
    cancellations = read_csv(CANCEL_PATH)
    print(f"Clean rows: {len(clean):,} | Cancellation rows: {len(cancellations):,}\n")

    check_invoice_consistency(clean)

    customers = build_customers(clean)
    products = build_products(clean)
    invoices = build_invoices(clean)
    items = build_items(clean)
    cancel_items = build_cancellations(cancellations)

    conn = create_database()
    print()
    # dependency order: parents before children
    insert(conn, customers, "customers")
    insert(conn, products, "products")
    insert(conn, invoices, "invoices")
    insert(conn, items, "invoice_items")
    insert(conn, cancel_items, "cancellation_items")
    conn.commit()

    verify(conn, clean, cancellations, customers, products, invoices)
    conn.close()


if __name__ == "__main__":
    main()