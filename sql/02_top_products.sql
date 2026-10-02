-- Top 10 products by revenue. Fees, postage and vouchers are excluded (is_product = 1).
SELECT
    p.stock_code,
    p.description,
    ROUND(SUM(it.line_total), 2) AS revenue,
    SUM(it.quantity)             AS units_sold
FROM invoice_items it
JOIN products p ON p.stock_code = it.stock_code
WHERE p.is_product = 1
GROUP BY p.stock_code, p.description
ORDER BY revenue DESC
LIMIT 10;