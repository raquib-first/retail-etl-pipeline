-- Gross sales, cancellations (negative amounts) and net revenue per month.
-- A cancellation is counted in the month it was made, not the month of the original sale.
WITH lines AS (
    SELECT strftime('%Y-%m', i.invoice_date) AS month, it.line_total AS amount, 'sale' AS kind
    FROM invoices i
    JOIN invoice_items it ON it.invoice_no = i.invoice_no
    UNION ALL
    SELECT strftime('%Y-%m', invoice_date), line_total, 'cancel'
    FROM cancellation_items
)
SELECT
    month,
    ROUND(SUM(CASE WHEN kind = 'sale'   THEN amount ELSE 0 END), 2) AS gross_revenue,
    ROUND(SUM(CASE WHEN kind = 'cancel' THEN amount ELSE 0 END), 2) AS cancellations,
    ROUND(SUM(amount), 2)                                          AS net_revenue
FROM lines
GROUP BY month
ORDER BY month;