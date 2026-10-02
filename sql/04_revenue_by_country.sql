-- Revenue, known-customer count and share of total revenue per country.
-- COUNT(DISTINCT customer_id) ignores NULLs, so customers = identified customers only.
SELECT
    i.country,
    ROUND(SUM(it.line_total), 2)  AS revenue,
    COUNT(DISTINCT i.customer_id) AS customers,
    ROUND(100.0 * SUM(it.line_total) / (SELECT SUM(line_total) FROM invoice_items), 2) AS pct_of_total
FROM invoices i
JOIN invoice_items it ON it.invoice_no = i.invoice_no
GROUP BY i.country
ORDER BY revenue DESC;