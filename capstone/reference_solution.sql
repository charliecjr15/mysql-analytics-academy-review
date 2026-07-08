-- Instructor/reference solution. Attempt the capstone before reading this file.
USE beanroute_capstone;

-- 01 PROFILE: preserve source rows and quantify known quality risks.
SELECT COUNT(*) AS products_total,
       SUM(category IS NULL OR TRIM(category) = '') AS missing_categories,
       SUM(current_price IS NULL OR current_price < 0) AS invalid_current_prices
FROM products;
SELECT COUNT(*) AS item_rows,
       SUM(quantity IS NULL OR quantity <= 0) AS invalid_quantities,
       SUM(unit_price IS NULL OR unit_price < 0) AS invalid_unit_prices,
       SUM(raw_product_name <> TRIM(raw_product_name)) AS names_with_outer_spaces
FROM order_items;
SELECT LOWER(TRIM(raw_product_name)) AS normalized_name, COUNT(DISTINCT raw_product_name) AS variants
FROM order_items GROUP BY normalized_name HAVING COUNT(DISTINCT raw_product_name) > 1;

-- 02 CLEAN: do not invent unknown quantities or prices. Create an analysis view
-- that standardizes text and flags unusable rows while retaining raw evidence.
CREATE OR REPLACE VIEW clean_order_items_v AS
SELECT oi.order_item_id, oi.order_id, oi.product_id,
       TRIM(oi.raw_product_name) AS clean_product_name,
       oi.quantity, oi.unit_price,
       CASE WHEN oi.quantity IS NULL OR oi.quantity <= 0
                  OR oi.unit_price IS NULL OR oi.unit_price < 0 THEN 0 ELSE 1 END AS valid_metric_row
FROM order_items oi;

-- 03A: completed metrics by store and month. One row per store-month.
SELECT s.store_name, DATE_FORMAT(o.order_date, '%Y-%m') AS order_month,
       COUNT(DISTINCT o.order_id) AS completed_orders,
       SUM(ci.quantity) AS units,
       SUM(ci.quantity * ci.unit_price) AS revenue
FROM orders o JOIN stores s ON s.store_id = o.store_id
JOIN clean_order_items_v ci ON ci.order_id = o.order_id AND ci.valid_metric_row = 1
WHERE o.status = 'completed'
GROUP BY s.store_id, s.store_name, DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY order_month, s.store_name;

-- 03B: product revenue rank inside category. Preserve ties with DENSE_RANK.
WITH product_revenue AS (
  SELECT p.category, p.product_id, p.product_name,
         SUM(ci.quantity * ci.unit_price) AS revenue
  FROM orders o JOIN clean_order_items_v ci ON ci.order_id = o.order_id AND ci.valid_metric_row = 1
  JOIN products p ON p.product_id = ci.product_id
  WHERE o.status = 'completed'
  GROUP BY p.category, p.product_id, p.product_name
), ranked AS (
  SELECT *, DENSE_RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS revenue_rank
  FROM product_revenue
)
SELECT * FROM ranked WHERE revenue_rank = 1 ORDER BY category, product_id;

-- 03C: store-month revenue compared with the company average for that month.
WITH store_month AS (
  SELECT o.store_id, DATE_FORMAT(o.order_date, '%Y-%m') AS order_month,
         SUM(ci.quantity * ci.unit_price) AS revenue
  FROM orders o JOIN clean_order_items_v ci ON ci.order_id = o.order_id AND ci.valid_metric_row = 1
  WHERE o.status = 'completed' GROUP BY o.store_id, DATE_FORMAT(o.order_date, '%Y-%m')
)
SELECT s.store_name, sm.order_month, sm.revenue,
       AVG(sm.revenue) OVER (PARTITION BY sm.order_month) AS company_store_average,
       sm.revenue - AVG(sm.revenue) OVER (PARTITION BY sm.order_month) AS difference_from_average
FROM store_month sm JOIN stores s ON s.store_id = sm.store_id
ORDER BY sm.order_month, sm.revenue DESC;

-- 03D: no completed purchase in the 30 days ending at the dataset's latest date.
WITH boundary AS (SELECT MAX(order_date) AS latest_date FROM orders)
SELECT c.customer_id, c.customer_name
FROM customers c CROSS JOIN boundary b
WHERE NOT EXISTS (
  SELECT 1 FROM orders o
  WHERE o.customer_id = c.customer_id AND o.status = 'completed'
    AND o.order_date > DATE_SUB(b.latest_date, INTERVAL 30 DAY)
    AND o.order_date <= b.latest_date
)
ORDER BY c.customer_id;

-- 03E: month-over-month completed revenue by store.
WITH monthly AS (
  SELECT o.store_id, DATE_FORMAT(o.order_date, '%Y-%m') AS order_month,
         SUM(ci.quantity * ci.unit_price) AS revenue
  FROM orders o JOIN clean_order_items_v ci ON ci.order_id = o.order_id AND ci.valid_metric_row = 1
  WHERE o.status = 'completed' GROUP BY o.store_id, DATE_FORMAT(o.order_date, '%Y-%m')
), compared AS (
  SELECT *, LAG(revenue) OVER (PARTITION BY store_id ORDER BY order_month) AS prior_revenue
  FROM monthly
)
SELECT s.store_name, c.order_month, c.revenue, c.prior_revenue,
       ROUND(100 * (c.revenue - c.prior_revenue) / NULLIF(c.prior_revenue, 0), 1) AS pct_change
FROM compared c JOIN stores s ON s.store_id = c.store_id
ORDER BY s.store_name, c.order_month;

-- 04 REPORTING VIEW: one row per valid, completed order item.
CREATE OR REPLACE VIEW completed_sales_v AS
SELECT o.order_id, o.order_date, o.store_id, s.store_name, o.customer_id,
       ci.order_item_id, ci.product_id, p.product_name, p.category,
       ci.quantity, ci.unit_price, ci.quantity * ci.unit_price AS revenue
FROM orders o JOIN stores s ON s.store_id = o.store_id
JOIN clean_order_items_v ci ON ci.order_id = o.order_id AND ci.valid_metric_row = 1
JOIN products p ON p.product_id = ci.product_id
WHERE o.status = 'completed';

-- QA reconciliation: both totals must match.
SELECT (SELECT SUM(revenue) FROM completed_sales_v) AS view_revenue,
       (SELECT SUM(oi.quantity * oi.unit_price)
        FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
        WHERE o.status = 'completed' AND oi.quantity > 0 AND oi.unit_price >= 0) AS source_revenue;

-- 05 PERFORMANCE: collect EXPLAIN before and after creating this index.
EXPLAIN SELECT store_id, order_date FROM orders
WHERE order_date >= '2026-03-01' AND order_date < '2026-04-01' AND status = 'completed';
CREATE INDEX idx_orders_status_date_store ON orders(status, order_date, store_id);
EXPLAIN SELECT store_id, order_date FROM orders
WHERE order_date >= '2026-03-01' AND order_date < '2026-04-01' AND status = 'completed';
