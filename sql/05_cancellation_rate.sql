-- Normal vs cancelled invoices per month.
-- rate = cancelled / (normal + cancelled). The months CTE keeps months
-- that have no cancellations (or no sales) from disappearing.
WITH normal AS (
    SELECT strftime('%Y-%m', invoice_date) AS month,
           COUNT(*)                        AS normal_invoices
    FROM invoices
    GROUP BY month
),
cancelled AS (
    SELECT strftime('%Y-%m', invoice_date) AS month,
           COUNT(DISTINCT invoice_no)      AS cancelled_invoices
    FROM cancellation_items
    GROUP BY month
),
months AS (
    SELECT month FROM normal
    UNION
    SELECT month FROM cancelled
)
SELECT
    m.month,
    COALESCE(n.normal_invoices, 0)    AS normal_invoices,
    COALESCE(c.cancelled_invoices, 0) AS cancelled_invoices,
    ROUND(100.0 * COALESCE(c.cancelled_invoices, 0)
          / (COALESCE(n.normal_invoices, 0) + COALESCE(c.cancelled_invoices, 0)), 2) AS cancellation_rate_pct
FROM months m
LEFT JOIN normal n    ON n.month = m.month
LEFT JOIN cancelled c ON c.month = m.month
ORDER BY m.month;