import pandas as pd

# PREDICTION (fill in before running):
# Quantity: ...
# UnitPrice: ...

def section(title):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)

# ---------- LOAD ----------
df = pd.read_csv("data/raw_data/Online_Retail.csv")

# ---------- Q1: SHAPE AND DATA TYPES ----------
section("1. SHAPE AND DATA TYPES")
print("Rows:", df.shape[0])
print("Columns:", df.shape[1])
print()
print(df.dtypes)

# ---------- Q2: NULL VALUES ----------
section("2. NULL VALUES")
nulls = pd.DataFrame({
    "null_count": df.isna().sum(),
    "null_percent": (df.isna().sum() / len(df) * 100).round(2),
})
print(nulls)

# ---------- Q3: DUPLICATES ----------
section("3. DUPLICATE ROWS")
dup_count = df.duplicated().sum()
print("Fully duplicated rows:", dup_count)
print("Percent of data:", round(dup_count / len(df) * 100, 2), "%")

# ---------- Q4: QUANTITY AND UNITPRICE ----------
section("4. QUANTITY AND UNITPRICE")
cols = df[["Quantity", "UnitPrice"]]
print("MIN:\n", cols.min(), "\n")
print("MAX:\n", cols.max(), "\n")
print("MEAN:\n", cols.mean(), "\n")

neg_qty = (df["Quantity"] < 0).sum()
bad_price = (df["UnitPrice"] <= 0).sum()
print("Rows with negative Quantity:", neg_qty)
print("Rows with UnitPrice <= 0:", bad_price)

# ---------- Q5: CANCELLED INVOICES ----------
section("5. CANCELLED INVOICES")
invoice = df["InvoiceNo"].astype(str)
cancelled = invoice.str.startswith("C").sum()
print("Invoices starting with 'C':", cancelled)
print("Negative Quantity rows (for comparison):", neg_qty)

# ---------- Q6: DATE RANGE ----------
section("6. DATE RANGE")
dates = pd.to_datetime(df["InvoiceDate"])
print("Start:", dates.min())
print("End:  ", dates.max())

# ---------- BONUS: UNIQUE COUNTS ----------
section("BONUS. UNIQUE COUNTS")
print("Customers:", df["CustomerID"].nunique())
print("Products: ", df["StockCode"].nunique())
print("Countries:", df["Country"].nunique())