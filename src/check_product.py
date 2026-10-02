import sqlite3
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_rows", 200)

conn = sqlite3.connect("data/retail.db")
print(pd.read_sql(
    "SELECT stock_code, description FROM products WHERE is_product = 0 ORDER BY stock_code",
    conn,
))
conn.close()