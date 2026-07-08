-- MetroMart starter practice questions.
-- Run retail_project_setup.sql first.
USE metromart_project;

-- 01. Inspect row counts and date range.
SELECT 'orders' AS table_name, COUNT(*) AS row_count FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'returns', COUNT(*) FROM returns;

SELECT MIN(order_date) AS first_order_at, MAX(order_date) AS last_order_at
FROM orders;

-- 02. Basic filtering and sorting.
SELECT order_id, order_date, channel, status, payment_method
FROM orders
WHERE status = 'completed'
ORDER BY order_date
LIMIT 20;

-- 03. Row-level revenue calculation.
SELECT
    order_item_id,
    quantity,
    unit_price,
    discount_amount,
    quantity * unit_price - discount_amount AS gross_item_revenue
FROM order_items
WHERE quantity > 0 AND unit_price >= 0
ORDER BY gross_item_revenue DESC
LIMIT 20;

-- 04. Completed monthly sales by store.
SELECT
    s.store_name,
    DATE_FORMAT(o.order_date, '%Y-%m') AS sales_month,
    COUNT(DISTINCT o.order_id) AS completed_orders,
    SUM(oi.quantity) AS units,
    SUM(oi.quantity * oi.unit_price - oi.discount_amount) AS gross_revenue
FROM orders AS o
JOIN stores AS s ON s.store_id = o.store_id
JOIN order_items AS oi ON oi.order_id = o.order_id
WHERE o.status = 'completed'
  AND oi.quantity > 0
  AND oi.unit_price >= 0
GROUP BY s.store_id, s.store_name, DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY sales_month, gross_revenue DESC;

-- 05. HAVING: products with at least 300 units sold.
SELECT
    p.product_name,
    SUM(oi.quantity) AS units
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.status = 'completed'
  AND oi.quantity > 0
  AND oi.unit_price >= 0
GROUP BY p.product_id, p.product_name
HAVING SUM(oi.quantity) >= 300
ORDER BY units DESC;

-- 06. LEFT JOIN: products with no valid completed sales.
SELECT
    p.product_id,
    p.product_name,
    COUNT(oi.order_item_id) AS valid_completed_item_rows
FROM products AS p
LEFT JOIN order_items AS oi
    ON oi.product_id = p.product_id
   AND oi.quantity > 0
   AND oi.unit_price >= 0
LEFT JOIN orders AS o
    ON o.order_id = oi.order_id
   AND o.status = 'completed'
GROUP BY p.product_id, p.product_name
HAVING COUNT(o.order_id) = 0;

-- 07. Self join: employee manager hierarchy.
SELECT
    e.employee_name,
    e.job_title,
    m.employee_name AS manager_name
FROM employees AS e
LEFT JOIN employees AS m ON m.employee_id = e.manager_id
ORDER BY manager_name, e.employee_name;

-- 08. CTE: monthly product revenue above the product average.
WITH product_month AS (
    SELECT
        p.product_id,
        p.product_name,
        DATE_FORMAT(o.order_date, '%Y-%m') AS sales_month,
        SUM(oi.quantity * oi.unit_price - oi.discount_amount) AS revenue
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    JOIN products AS p ON p.product_id = oi.product_id
    WHERE o.status = 'completed'
      AND oi.quantity > 0
      AND oi.unit_price >= 0
    GROUP BY p.product_id, p.product_name, DATE_FORMAT(o.order_date, '%Y-%m')
), product_average AS (
    SELECT product_id, AVG(revenue) AS avg_monthly_revenue
    FROM product_month
    GROUP BY product_id
)
SELECT pm.*
FROM product_month AS pm
JOIN product_average AS pa ON pa.product_id = pm.product_id
WHERE pm.revenue > pa.avg_monthly_revenue
ORDER BY pm.product_name, pm.sales_month;

-- 09. Window ranking: top three products per department.
WITH product_sales AS (
    SELECT
        pc.department,
        p.product_name,
        SUM(oi.quantity * oi.unit_price - oi.discount_amount) AS revenue
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    JOIN products AS p ON p.product_id = oi.product_id
    JOIN product_categories AS pc ON pc.category_id = p.category_id
    WHERE o.status = 'completed'
      AND oi.quantity > 0
      AND oi.unit_price >= 0
    GROUP BY pc.department, p.product_id, p.product_name
), ranked AS (
    SELECT
        product_sales.*,
        DENSE_RANK() OVER (PARTITION BY department ORDER BY revenue DESC) AS revenue_rank
    FROM product_sales
)
SELECT *
FROM ranked
WHERE revenue_rank <= 3
ORDER BY department, revenue_rank, product_name;

-- 10. CASE, dates, and text cleaning.
SELECT
    customer_id,
    TRIM(customer_name) AS clean_name,
    LOWER(TRIM(email)) AS clean_email,
    CASE
        WHEN email IS NULL OR TRIM(email) = '' THEN 'missing email'
        WHEN email NOT LIKE '%@%.%' THEN 'invalid email'
        ELSE 'usable email'
    END AS email_quality,
    CASE
        WHEN loyalty_tier IS NULL THEN 'Unknown'
        ELSE CONCAT(UPPER(LEFT(TRIM(loyalty_tier), 1)), LOWER(SUBSTRING(TRIM(loyalty_tier), 2)))
    END AS normalized_tier,
    TIMESTAMPDIFF(YEAR, birth_date, CURRENT_DATE) AS approximate_age
FROM customers
ORDER BY customer_id
LIMIT 50;

-- 11. Data-quality tests.
SELECT 'invalid item metrics' AS test_name, COUNT(*) AS failures
FROM order_items
WHERE quantity IS NULL OR quantity <= 0 OR unit_price IS NULL OR unit_price < 0
UNION ALL
SELECT 'blank customer city', COUNT(*)
FROM customers
WHERE city IS NULL OR TRIM(city) = ''
UNION ALL
SELECT 'feedback rating outside 1-5', COUNT(*)
FROM customer_feedback
WHERE rating IS NULL OR rating NOT BETWEEN 1 AND 5;

-- 12. Build a trusted reporting view.
CREATE OR REPLACE VIEW completed_valid_sales_v AS
SELECT
    o.order_id,
    DATE(o.order_date) AS order_date,
    DATE_FORMAT(o.order_date, '%Y-%m') AS sales_month,
    r.region_name,
    s.store_name,
    o.channel,
    o.customer_id,
    p.product_id,
    p.product_name,
    pc.category_name,
    pc.department,
    oi.order_item_id,
    oi.quantity,
    oi.unit_price,
    oi.discount_amount,
    oi.quantity * oi.unit_price - oi.discount_amount AS gross_revenue
FROM orders AS o
JOIN stores AS s ON s.store_id = o.store_id
JOIN regions AS r ON r.region_id = s.region_id
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
JOIN product_categories AS pc ON pc.category_id = p.category_id
WHERE o.status = 'completed'
  AND oi.quantity > 0
  AND oi.unit_price >= 0;

SELECT sales_month, SUM(gross_revenue) AS gross_revenue
FROM completed_valid_sales_v
GROUP BY sales_month
ORDER BY sales_month;

-- 13. EXPLAIN and index practice.
EXPLAIN
SELECT store_id, order_date, status
FROM orders
WHERE status = 'completed'
  AND order_date >= '2026-03-01'
  AND order_date < '2026-04-01';

CREATE INDEX idx_orders_status_date_store
ON orders(status, order_date, store_id);

EXPLAIN
SELECT store_id, order_date, status
FROM orders
WHERE status = 'completed'
  AND order_date >= '2026-03-01'
  AND order_date < '2026-04-01';
