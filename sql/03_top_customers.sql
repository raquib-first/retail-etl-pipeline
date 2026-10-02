-- Top 10 customers by revenue. Rows with no customer are excluded.
SELECT
    i.customer_id,
    ROUND(SUM(it.line_total), 2) AS revenue,
    COUNT(DISTINCT i.invoice_no) AS orders
FROM invoices i
JOIN invoice_items it ON it.invoice_no = i.invoice_no
WHERE i.customer_id IS NOT NULL
GROUP BY i.customer_id
ORDER BY revenue DESC
LIMIT 10;