CREATE TABLE products (
    stock_code  TEXT PRIMARY KEY,
    description TEXT,
    is_product  INTEGER NOT NULL DEFAULT 1
);