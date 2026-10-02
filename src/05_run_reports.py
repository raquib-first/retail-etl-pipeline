import glob
import os
import sqlite3
import pandas as pd

DB_PATH = "data/retail.db"
SQL_DIR = "sql"
OUT_DIR = "reports"

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

os.makedirs(OUT_DIR, exist_ok=True)
conn = sqlite3.connect(DB_PATH)

for path in sorted(glob.glob(os.path.join(SQL_DIR, "0*.sql"))):
    name = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding="utf-8") as f:
        query = f.read()
    df = pd.read_sql(query, conn)
    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)
    print(df.to_string(index=False))
    df.to_csv(os.path.join(OUT_DIR, f"{name}.csv"), index=False)

conn.close()