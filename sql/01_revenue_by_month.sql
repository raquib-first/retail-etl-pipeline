-- Revenue, invoice count and average order value per month.
-- Total revenue includes postage and fees (real income).
-- Note: 2011-12 is a partial month (data ends 2011-12-09).
SELECT
    strftime('%Y-%m', i.invoice_date)                          AS month,
    ROUND(SUM(it.line_total), 2)                               AS revenue,
    COUNT(DISTINCT i.invoice_no)                               AS invoices,
    ROUND(SUM(it.line_total) / COUNT(DISTINCT i.invoice_no), 2) AS avg_order_value
FROM invoices i
JOIN invoice_items it ON it.invoice_no = i.invoice_no
GROUP BY month
ORDER BY month;