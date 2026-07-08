# MetroMart Analyst Workday Walkthrough

This walkthrough treats the MetroMart dataset like a real work assignment. You
are not just running SQL. You are turning messy operational data into a trusted
monthly performance report.

## The Work Request

Your operations director asks:

> We need a monthly retail performance report for January through June 2026.
> Show sales by store, region, channel, department, category, and product. We
> also need to know which products are growing, which stores are underperforming,
> what returns are doing, and whether the data is clean enough to trust.

Your job for the day:

1. Confirm the database loaded correctly.
2. Understand the schema and result grain.
3. Profile the raw data before trusting it.
4. Define business rules for valid sales.
5. Build a clean reporting view.
6. Answer the core business questions.
7. Validate totals.
8. Add performance evidence.
9. Write a short analyst summary.

## Step 0: Start the Assignment

Run the setup script first.

```sql
SOURCE project_data/retail_project_setup.sql;
USE metromart_project;
```

If your SQL editor does not support `SOURCE`, open
`project_data/retail_project_setup.sql`, select the full script, and execute it.

Expected setup idea:

- `orders` should have 1,800 rows.
- `order_items` should have 5,400 rows.
- The reporting period should run across January-June 2026.

## Step 1: Confirm Row Counts and Date Range

As an analyst, your first task is not the final report. It is making sure the
data you received is the data you think you received.

```sql
SELECT 'regions' AS table_name, COUNT(*) AS row_count FROM regions
UNION ALL SELECT 'stores', COUNT(*) FROM stores
UNION ALL SELECT 'employees', COUNT(*) FROM employees
UNION ALL SELECT 'product_categories', COUNT(*) FROM product_categories
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'returns', COUNT(*) FROM returns
UNION ALL SELECT 'inventory_snapshots', COUNT(*) FROM inventory_snapshots
UNION ALL SELECT 'customer_feedback', COUNT(*) FROM customer_feedback
UNION ALL SELECT 'raw_customer_import', COUNT(*) FROM raw_customer_import;
```

Then check the time window.

```sql
SELECT
    MIN(order_date) AS first_order_at,
    MAX(order_date) AS last_order_at,
    COUNT(*) AS order_rows
FROM orders;
```

What you are doing:

- Verifying table presence.
- Verifying row volume.
- Finding the calendar period.
- Catching setup mistakes before building analysis on top of them.

## Step 2: Read the Schema Like a Business System

Before writing KPI queries, identify the grain of the important tables.

```sql
DESCRIBE orders;
DESCRIBE order_items;
DESCRIBE products;
DESCRIBE stores;
DESCRIBE customers;
```

Working notes:

- `orders`: one row per checkout/order event.
- `order_items`: one row per product line inside an order.
- `products`: one row per product.
- `stores`: one row per store.
- `customers`: one row per customer record.
- `returns`: one row per returned item event.

Important analyst rule:

> Revenue lives at the order-item grain, not the order grain.

That means a revenue query must usually include `order_items`.

## Step 3: Inspect Order Status and Channels

The business request says "sales," but operational systems include cancelled,
pending, and refunded activity. First, measure the populations.

```sql
SELECT
    status,
    COUNT(*) AS order_count
FROM orders
GROUP BY status
ORDER BY order_count DESC;
```

```sql
SELECT
    channel,
    COUNT(*) AS order_count
FROM orders
GROUP BY channel
ORDER BY order_count DESC;
```

Decision:

- Use `status = 'completed'` for completed sales.
- Do not mix cancelled or pending orders into revenue.
- Treat returns separately and subtract valid refunds when calculating net revenue.

## Step 4: Profile Metric Quality Before Calculating Revenue

A query can run and still answer the wrong question. Check invalid rows before
you trust `quantity * unit_price`.

```sql
SELECT
    COUNT(*) AS item_rows,
    SUM(quantity IS NULL) AS null_quantity_rows,
    SUM(quantity <= 0) AS non_positive_quantity_rows,
    SUM(unit_price IS NULL) AS null_price_rows,
    SUM(unit_price < 0) AS negative_price_rows,
    SUM(discount_amount < 0) AS negative_discount_rows
FROM order_items;
```

Preview the problem rows.

```sql
SELECT
    order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount_amount,
    raw_product_name
FROM order_items
WHERE quantity IS NULL
   OR quantity <= 0
   OR unit_price IS NULL
   OR unit_price < 0
   OR discount_amount < 0
ORDER BY order_item_id;
```

Business rule:

- Exclude rows where `quantity` is `NULL` or `<= 0`.
- Exclude rows where `unit_price` is `NULL` or `< 0`.
- Keep the raw rows available for audit. Do not delete them.

## Step 5: Profile Customer Data Quality

This matters because customer reports, retention analysis, and marketing exports
depend on usable customer data.

```sql
SELECT
    COUNT(*) AS customer_rows,
    SUM(email IS NULL OR TRIM(email) = '') AS missing_email_rows,
    SUM(email IS NOT NULL AND email NOT LIKE '%@%.%') AS suspicious_email_rows,
    SUM(city IS NULL OR TRIM(city) = '') AS blank_city_rows,
    SUM(loyalty_tier IS NULL OR TRIM(loyalty_tier) = '') AS missing_tier_rows
FROM customers;
```

Look for duplicate-like emails after trimming and lowercasing.

```sql
SELECT
    LOWER(TRIM(email)) AS normalized_email,
    COUNT(*) AS customer_count
FROM customers
WHERE email IS NOT NULL AND TRIM(email) <> ''
GROUP BY LOWER(TRIM(email))
HAVING COUNT(*) > 1
ORDER BY customer_count DESC, normalized_email;
```

What you are doing:

- Separating data-quality work from sales KPI work.
- Finding whether customer analysis can be trusted.
- Identifying cleanup tasks without changing source data yet.

## Step 6: Profile Product Name Messiness

The trusted relationship is `order_items.product_id -> products.product_id`.
The raw product name is intentionally messy for cleaning practice.

```sql
SELECT
    LOWER(TRIM(raw_product_name)) AS normalized_raw_name,
    COUNT(*) AS item_rows,
    COUNT(DISTINCT raw_product_name) AS raw_variants
FROM order_items
GROUP BY LOWER(TRIM(raw_product_name))
HAVING COUNT(DISTINCT raw_product_name) > 1
ORDER BY raw_variants DESC, item_rows DESC;
```

Decision:

- Use `products.product_name` for final reporting.
- Use `raw_product_name` to explain data-quality issues.

## Step 7: Build the Trusted Reporting View

Now create a reusable layer with your business rules baked in. This is your
main analyst deliverable because it gives future queries one clean source.

```sql
CREATE OR REPLACE VIEW completed_valid_sales_v AS
SELECT
    o.order_id,
    DATE(o.order_date) AS order_date,
    DATE_FORMAT(o.order_date, '%Y-%m') AS sales_month,
    o.channel,
    o.payment_method,
    r.region_id,
    r.region_name,
    s.store_id,
    s.store_name,
    s.city AS store_city,
    c.customer_id,
    c.customer_name,
    p.product_id,
    p.product_name,
    pc.category_id,
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
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
JOIN product_categories AS pc ON pc.category_id = p.category_id
WHERE o.status = 'completed'
  AND oi.quantity > 0
  AND oi.unit_price >= 0;
```

Result grain:

> One row per valid item line from a completed order.

That sentence matters. If you cannot state result grain, you are not ready to
interpret the numbers.

## Step 8: Reconcile the View Against the Source

Before using the view, prove it did not accidentally change the math.

```sql
SELECT
    (SELECT COUNT(*) FROM completed_valid_sales_v) AS view_rows,
    (SELECT COUNT(*)
     FROM orders AS o
     JOIN order_items AS oi ON oi.order_id = o.order_id
     WHERE o.status = 'completed'
       AND oi.quantity > 0
       AND oi.unit_price >= 0) AS source_rows;
```

```sql
SELECT
    (SELECT ROUND(SUM(gross_revenue), 2)
     FROM completed_valid_sales_v) AS view_gross_revenue,
    (SELECT ROUND(SUM(oi.quantity * oi.unit_price - oi.discount_amount), 2)
     FROM orders AS o
     JOIN order_items AS oi ON oi.order_id = o.order_id
     WHERE o.status = 'completed'
       AND oi.quantity > 0
       AND oi.unit_price >= 0) AS source_gross_revenue;
```

If these do not match, stop. Fix the view before continuing.

## Step 9: Calculate the Executive Monthly KPI Trend

Now you can answer the first business question.

```sql
SELECT
    sales_month,
    COUNT(DISTINCT order_id) AS completed_orders,
    SUM(quantity) AS units_sold,
    ROUND(SUM(gross_revenue), 2) AS gross_revenue,
    ROUND(SUM(gross_revenue) / COUNT(DISTINCT order_id), 2) AS revenue_per_order
FROM completed_valid_sales_v
GROUP BY sales_month
ORDER BY sales_month;
```

What to look for:

- Highest revenue month.
- Lowest revenue month.
- Whether orders and revenue move together.
- Whether revenue per order is changing.

## Step 10: Sales by Region, Store, and Channel

Operations leaders usually ask where performance is coming from.

```sql
SELECT
    sales_month,
    region_name,
    store_name,
    channel,
    COUNT(DISTINCT order_id) AS completed_orders,
    SUM(quantity) AS units_sold,
    ROUND(SUM(gross_revenue), 2) AS gross_revenue
FROM completed_valid_sales_v
GROUP BY sales_month, region_name, store_name, channel
ORDER BY sales_month, region_name, gross_revenue DESC;
```

If this result is too detailed, roll it up.

```sql
SELECT
    region_name,
    store_name,
    COUNT(DISTINCT order_id) AS completed_orders,
    ROUND(SUM(gross_revenue), 2) AS gross_revenue
FROM completed_valid_sales_v
GROUP BY region_name, store_name
ORDER BY gross_revenue DESC;
```

## Step 11: Product and Category Performance

Start with category and department.

```sql
SELECT
    department,
    category_name,
    SUM(quantity) AS units_sold,
    ROUND(SUM(gross_revenue), 2) AS gross_revenue
FROM completed_valid_sales_v
GROUP BY department, category_name
ORDER BY gross_revenue DESC;
```

Then rank products.

```sql
SELECT
    product_name,
    category_name,
    SUM(quantity) AS units_sold,
    ROUND(SUM(gross_revenue), 2) AS gross_revenue
FROM completed_valid_sales_v
GROUP BY product_id, product_name, category_name
ORDER BY gross_revenue DESC
LIMIT 10;
```

Analyst note:

- Units answer volume.
- Revenue answers money.
- They are related, but they are not the same metric.

## Step 12: Use HAVING for Business Thresholds

Find products with enough volume to matter operationally.

```sql
SELECT
    product_name,
    SUM(quantity) AS units_sold,
    ROUND(SUM(gross_revenue), 2) AS gross_revenue
FROM completed_valid_sales_v
GROUP BY product_id, product_name
HAVING SUM(quantity) >= 300
ORDER BY units_sold DESC;
```

Why `HAVING`:

- `WHERE` filters detail rows before grouping.
- `HAVING` filters completed groups after `SUM(quantity)` exists.

## Step 13: Use CTEs for Monthly Product Movement

Now answer which products are above or below their own average month.

```sql
WITH product_month AS (
    SELECT
        product_id,
        product_name,
        sales_month,
        ROUND(SUM(gross_revenue), 2) AS revenue
    FROM completed_valid_sales_v
    GROUP BY product_id, product_name, sales_month
), product_average AS (
    SELECT
        product_id,
        ROUND(AVG(revenue), 2) AS avg_monthly_revenue
    FROM product_month
    GROUP BY product_id
)
SELECT
    pm.product_name,
    pm.sales_month,
    pm.revenue,
    pa.avg_monthly_revenue,
    ROUND(pm.revenue - pa.avg_monthly_revenue, 2) AS difference_from_average
FROM product_month AS pm
JOIN product_average AS pa ON pa.product_id = pm.product_id
ORDER BY pm.product_name, pm.sales_month;
```

What you are doing:

- First CTE: monthly revenue per product.
- Second CTE: benchmark per product.
- Final query: compare each month with that product's normal performance.

## Step 14: Use Window Functions for Rankings

Rank top products inside each department.

```sql
WITH product_sales AS (
    SELECT
        department,
        category_name,
        product_name,
        ROUND(SUM(gross_revenue), 2) AS revenue
    FROM completed_valid_sales_v
    GROUP BY department, category_name, product_id, product_name
), ranked AS (
    SELECT
        product_sales.*,
        DENSE_RANK() OVER (
            PARTITION BY department
            ORDER BY revenue DESC
        ) AS department_revenue_rank
    FROM product_sales
)
SELECT *
FROM ranked
WHERE department_revenue_rank <= 3
ORDER BY department, department_revenue_rank, product_name;
```

Why `DENSE_RANK`:

- It preserves ties.
- It ranks within each department separately.

## Step 15: Month-Over-Month Revenue Change

Use `LAG` to compare each store-month with the previous month.

```sql
WITH store_month AS (
    SELECT
        store_id,
        store_name,
        sales_month,
        ROUND(SUM(gross_revenue), 2) AS revenue
    FROM completed_valid_sales_v
    GROUP BY store_id, store_name, sales_month
), compared AS (
    SELECT
        store_month.*,
        LAG(revenue) OVER (
            PARTITION BY store_id
            ORDER BY sales_month
        ) AS prior_month_revenue
    FROM store_month
)
SELECT
    store_name,
    sales_month,
    revenue,
    prior_month_revenue,
    ROUND(
        100 * (revenue - prior_month_revenue) / NULLIF(prior_month_revenue, 0),
        1
    ) AS pct_change
FROM compared
ORDER BY store_name, sales_month;
```

Why `NULLIF`:

- It prevents division by zero.
- First month per store has no prior month, so the comparison is `NULL`.

## Step 16: Compare Stores With Their Region Average

This answers whether a store is underperforming relative to peers.

```sql
WITH store_month AS (
    SELECT
        region_name,
        store_name,
        sales_month,
        ROUND(SUM(gross_revenue), 2) AS revenue
    FROM completed_valid_sales_v
    GROUP BY region_name, store_name, sales_month
)
SELECT
    region_name,
    store_name,
    sales_month,
    revenue,
    ROUND(AVG(revenue) OVER (
        PARTITION BY region_name, sales_month
    ), 2) AS region_store_average,
    ROUND(revenue - AVG(revenue) OVER (
        PARTITION BY region_name, sales_month
    ), 2) AS difference_from_region_average
FROM store_month
ORDER BY sales_month, region_name, difference_from_region_average;
```

What to write down:

- Which stores are consistently below the region average?
- Is it one bad month or a pattern?
- Does the store have fewer orders, lower basket size, or a weaker product mix?

## Step 17: Analyze Returns and Net Revenue

Gross sales alone can overstate performance. Bring in returns.

```sql
WITH gross_sales AS (
    SELECT
        sales_month,
        ROUND(SUM(gross_revenue), 2) AS gross_revenue
    FROM completed_valid_sales_v
    GROUP BY sales_month
), refunds AS (
    SELECT
        DATE_FORMAT(r.return_date, '%Y-%m') AS refund_month,
        ROUND(SUM(r.refund_amount), 2) AS refund_amount
    FROM returns AS r
    GROUP BY DATE_FORMAT(r.return_date, '%Y-%m')
)
SELECT
    gs.sales_month,
    gs.gross_revenue,
    COALESCE(refunds.refund_amount, 0) AS refund_amount,
    ROUND(gs.gross_revenue - COALESCE(refunds.refund_amount, 0), 2) AS net_revenue
FROM gross_sales AS gs
LEFT JOIN refunds ON refunds.refund_month = gs.sales_month
ORDER BY gs.sales_month;
```

Decision to document:

- This subtracts refunds in the month the return happened.
- A different finance team might subtract refunds from the original sale month.
- Both are valid if clearly defined.

## Step 18: Return Rate by Product

Now identify products that may have quality or expectation issues.

```sql
WITH sold AS (
    SELECT
        product_id,
        product_name,
        COUNT(*) AS sold_item_rows,
        SUM(quantity) AS units_sold,
        SUM(gross_revenue) AS gross_revenue
    FROM completed_valid_sales_v
    GROUP BY product_id, product_name
), returned AS (
    SELECT
        oi.product_id,
        COUNT(*) AS returned_item_rows,
        SUM(r.refund_amount) AS refund_amount
    FROM returns AS r
    JOIN order_items AS oi ON oi.order_item_id = r.order_item_id
    GROUP BY oi.product_id
)
SELECT
    sold.product_name,
    sold.units_sold,
    ROUND(sold.gross_revenue, 2) AS gross_revenue,
    COALESCE(returned.returned_item_rows, 0) AS returned_item_rows,
    ROUND(COALESCE(returned.refund_amount, 0), 2) AS refund_amount,
    ROUND(100 * COALESCE(returned.returned_item_rows, 0) / sold.sold_item_rows, 2) AS return_row_rate_pct
FROM sold
LEFT JOIN returned ON returned.product_id = sold.product_id
ORDER BY return_row_rate_pct DESC, refund_amount DESC;
```

## Step 19: Inventory Risk

Find product-store combinations below reorder point in the latest snapshot.

```sql
WITH latest_snapshot AS (
    SELECT MAX(snapshot_date) AS snapshot_date
    FROM inventory_snapshots
)
SELECT
    s.store_name,
    p.product_name,
    i.snapshot_date,
    i.on_hand_quantity,
    i.reorder_point,
    i.on_hand_quantity - i.reorder_point AS quantity_gap
FROM inventory_snapshots AS i
JOIN latest_snapshot AS ls ON ls.snapshot_date = i.snapshot_date
JOIN stores AS s ON s.store_id = i.store_id
JOIN products AS p ON p.product_id = i.product_id
WHERE i.on_hand_quantity < i.reorder_point
ORDER BY quantity_gap, s.store_name, p.product_name;
```

Business interpretation:

- A top-selling product below reorder point is urgent.
- A slow product below reorder point may be less urgent.
- Join this with sales rank for better prioritization.

## Step 20: Customer Retention Question

Find customers with no completed purchase in the latest 45 days represented.

```sql
WITH boundary AS (
    SELECT MAX(DATE(order_date)) AS latest_order_date
    FROM orders
)
SELECT
    c.customer_id,
    c.customer_name,
    c.email,
    c.loyalty_tier
FROM customers AS c
CROSS JOIN boundary AS b
WHERE NOT EXISTS (
    SELECT 1
    FROM orders AS o
    WHERE o.customer_id = c.customer_id
      AND o.status = 'completed'
      AND DATE(o.order_date) > DATE_SUB(b.latest_order_date, INTERVAL 45 DAY)
      AND DATE(o.order_date) <= b.latest_order_date
)
ORDER BY c.customer_id;
```

Why `NOT EXISTS`:

- It expresses "no matching completed order in this period."
- It avoids common `NOT IN` surprises when `NULL` appears.

## Step 21: Create a Cleaning Log

In real work, cleaning choices should be reviewable.

```sql
CREATE TABLE IF NOT EXISTS cleaning_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    rule_name VARCHAR(120) NOT NULL,
    issue_count_before INT NOT NULL,
    action_taken VARCHAR(255) NOT NULL,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Log known issues.

```sql
INSERT INTO cleaning_log (
    table_name,
    rule_name,
    issue_count_before,
    action_taken
)
SELECT
    'order_items',
    'exclude invalid metric rows',
    COUNT(*),
    'Reporting view excludes rows where quantity is NULL or <= 0, or unit_price is NULL or < 0'
FROM order_items
WHERE quantity IS NULL
   OR quantity <= 0
   OR unit_price IS NULL
   OR unit_price < 0;
```

```sql
INSERT INTO cleaning_log (
    table_name,
    rule_name,
    issue_count_before,
    action_taken
)
SELECT
    'customers',
    'standardize customer contact fields',
    COUNT(*),
    'Use LOWER/TRIM for email analysis and flag missing or suspicious emails'
FROM customers
WHERE email IS NULL
   OR TRIM(email) = ''
   OR email NOT LIKE '%@%.%'
   OR city IS NULL
   OR TRIM(city) = '';
```

Review the log.

```sql
SELECT *
FROM cleaning_log
ORDER BY checked_at, log_id;
```

## Step 22: Performance Check

Pretend the March completed-order report is slow. First capture the plan.

```sql
EXPLAIN
SELECT
    store_id,
    order_date,
    status
FROM orders
WHERE status = 'completed'
  AND order_date >= '2026-03-01'
  AND order_date < '2026-04-01';
```

Add a composite index that matches the equality filter, range filter, and store
column used by the report.

```sql
CREATE INDEX idx_orders_status_date_store
ON orders(status, order_date, store_id);
```

Check the plan again.

```sql
EXPLAIN
SELECT
    store_id,
    order_date,
    status
FROM orders
WHERE status = 'completed'
  AND order_date >= '2026-03-01'
  AND order_date < '2026-04-01';
```

What to compare:

- `possible_keys`
- `key`
- `type`
- estimated `rows`
- `Extra`

Important:

> Do not claim the query is better just because an index exists. The plan and
> unchanged result are your evidence.

## Step 23: Final QA Checklist

Before sending anything, answer these:

- Did I define completed sales?
- Did I state the grain of the reporting view?
- Did I exclude invalid metric rows?
- Did I reconcile the reporting view to the source logic?
- Did I separate gross revenue from net revenue?
- Did I explain how returns are assigned to months?
- Did I check customer and product-name quality issues?
- Did I use CTEs/windows where they improve the question?
- Did I use `EXPLAIN` evidence for performance claims?

## Step 24: Analyst Summary Template

Use this format for your final project write-up.

```text
Business question
MetroMart requested a January-June 2026 retail performance report by month,
store, region, channel, department, category, and product, with quality checks
and return-aware revenue.

Data used
I used orders, order_items, products, product_categories, stores, regions,
customers, returns, inventory_snapshots, and customer_feedback.

Key definitions
Completed sales include only orders where status = 'completed'. Valid item rows
require quantity > 0 and unit_price >= 0. Gross revenue is quantity * unit_price
- discount_amount. Net revenue subtracts refunds in the month the return
happened.

Quality notes
The raw data includes invalid item metrics, product-name variants, missing or
suspicious customer contact fields, blank cities, and feedback ratings outside
the expected 1-5 range. I did not overwrite raw tables; I created a trusted
reporting view and logged cleaning decisions.

Main findings
1. [Write your strongest revenue finding.]
2. [Write your strongest product/category finding.]
3. [Write your strongest store/channel finding.]
4. [Write your strongest data-quality or inventory-risk finding.]

Recommendation
[State one action the operations team should take and the SQL evidence behind it.]

Limitations
This is simulated operational data. Customer identity cleanup, refund accounting
rules, and inventory timing should be confirmed with business owners before
production reporting.
```

## How to Use This Walkthrough

Do not paste everything at once. Work like this:

1. Run one section.
2. Look at the result.
3. Write one sentence describing the result grain.
4. Write one sentence describing what the result means.
5. Only then move to the next section.

That is how you move from "copying examples" to doing analyst work.
