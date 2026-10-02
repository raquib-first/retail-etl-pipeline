-- Top 10 products by NET revenue (sales minus cancellations).
-- Note: the JOIN drops cancelled codes that never appear in sales, since products
-- is built from clean sales only; this slightly overstates net revenue.
WITH lines AS (
    SELECT stock_code, quantity, line_total FROM invoice_items
    UNION ALL
    SELECT stock_code, quantity, line_total FROM cancellation_items
)
SELECT
    p.stock_code,
    p.description,
    ROUND(SUM(l.line_total), 2) AS net_revenue,
    SUM(l.quantity)             AS net_units
FROM lines l
JOIN products p ON p.stock_code = l.stock_code
WHERE p.is_product = 1
GROUP BY p.stock_code, p.description
ORDER BY net_revenue DESC
LIMIT 10;