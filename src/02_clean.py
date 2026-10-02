import pandas as pd

RAW_PATH = "data/raw_data/Online_Retail.csv"
OUT_DIR = "data/clean"


# ---------- STEP 1: LOAD ----------
def load_raw():
    df = pd.read_csv(RAW_PATH)
    print("Raw rows:", len(df))
    return df


# ---------- STEP 2: FIX TYPES AND TIDY TEXT ----------
def fix_types(df):
    df = df.copy()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["Description"] = df["Description"].str.strip()
    # float only because of nulls; nullable integer keeps NaN as <NA>
    df["CustomerID"] = df["CustomerID"].astype("Int64")
    return df


# ---------- STEP 3: REMOVE EXACT DUPLICATES ----------
def remove_duplicates(df):
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    print("Duplicates removed:", removed)
    return df, removed


# ---------- STEP 4: MISSING VALUES ----------
def flag_customer(df):
    # DECISION: keep rows with no CustomerID (they are real sales) and flag them,
    # instead of deleting about a quarter of the data.
    df = df.copy()
    df["has_customer"] = df["CustomerID"].notna()
    return df


# ---------- STEP 5: SPLIT CANCELLATIONS ----------
def split_cancellations(df):
    is_cancel = df["InvoiceNo"].str.startswith("C")
    return df[~is_cancel].copy(), df[is_cancel].copy()


# ---------- STEP 6: REJECT INVALID ROWS ----------
def split_rejected(df):
    # DECISION: rules are applied in priority order; the first match is the reason.
    # Check these against what you saw in your three data checks.
    reason = pd.Series(pd.NA, index=df.index, dtype="object")

    missing_desc = df["Description"].isna() | (df["Description"] == "")
    reason[missing_desc] = "missing_description"

    bad_price = (df["UnitPrice"] <= 0) & reason.isna()
    reason[bad_price] = "price_zero_or_negative"

    neg_qty = (df["Quantity"] < 0) & reason.isna()
    reason[neg_qty] = "negative_quantity_not_cancellation"

    rejected = df[reason.notna()].copy()
    rejected["reject_reason"] = reason[reason.notna()]
    clean = df[reason.isna()].copy()
    return clean, rejected


# ---------- STEP 7: DERIVED COLUMNS ----------
def add_derived(df):
    df = df.copy()
    df["LineTotal"] = (df["Quantity"] * df["UnitPrice"]).round(2)
    df["InvoiceMonth"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    return df


# ---------- STEP 8: SAVE ----------
def save_outputs(clean, cancellations, rejected):
    clean.to_csv(f"{OUT_DIR}/sales_clean.csv", index=False)
    cancellations.to_csv(f"{OUT_DIR}/cancellations.csv", index=False)
    rejected.to_csv(f"{OUT_DIR}/rejected.csv", index=False)


# ---------- STEP 9: RECONCILE ----------
def reconcile(raw_rows, dup_removed, cancellations, rejected, clean):
    total = dup_removed + len(cancellations) + len(rejected) + len(clean)
    print("\n" + "=" * 40)
    print("RECONCILIATION")
    print("=" * 40)
    print(f"{'Raw rows':<24}{raw_rows:>10,}")
    print(f"{'Duplicates removed':<24}{dup_removed:>10,}")
    print(f"{'Cancellations':<24}{len(cancellations):>10,}")
    print(f"{'Rejected':<24}{len(rejected):>10,}")
    print(f"{'Clean':<24}{len(clean):>10,}")
    print("-" * 40)
    print(f"{'Sum of groups':<24}{total:>10,}")
    assert total == raw_rows, "Row counts do not reconcile!"
    print("OK: every raw row is accounted for.")
    print("\nRejected by reason:")
    print(rejected["reject_reason"].value_counts())


def main():
    raw = load_raw()
    df = fix_types(raw)
    df, dup_removed = remove_duplicates(df)
    df = flag_customer(df)
    df, cancellations = split_cancellations(df)
    clean, rejected = split_rejected(df)

    clean = add_derived(clean)
    cancellations = add_derived(cancellations)

    save_outputs(clean, cancellations, rejected)
    reconcile(len(raw), dup_removed, cancellations, rejected, clean)
    print("\nVERIFICATION")
    print("Negative qty left in clean:", (clean["Quantity"] < 0).sum())
    print("Price <= 0 left in clean:  ", (clean["UnitPrice"] <= 0).sum())

    neg_rej = rejected[rejected["Quantity"] < 0]
    print("Negative qty inside rejected:", len(neg_rej))
    print(neg_rej["reject_reason"].value_counts())


if __name__ == "__main__":
    main()