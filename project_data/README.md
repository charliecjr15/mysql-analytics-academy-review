# MetroMart Project Dataset

This folder contains a larger simulated retail dataset for portfolio practice.
It is separate from the beginner `coffee_shop` lessons and the smaller capstone.

## What It Gives You

Run `retail_project_setup.sql` in MySQL 8.0+. It creates a dedicated
`metromart_project` database with:

- 6 stores across 4 regions
- 14 employees with a manager hierarchy
- 18 products across 8 categories
- 250 customers, including messy emails, blanks, duplicate-like rows, and tier variants
- 1,800 orders across January-June 2026
- 5,400 order item rows
- returns, inventory snapshots, customer feedback, promotions, and raw import data

The data is deterministic, so every reset creates the same rows.

## Practice Coverage

Use this dataset to practice the whole course:

- setup, reset, `CREATE TABLE`, data types, primary keys, and foreign keys
- `SELECT`, aliases, `WHERE`, `ORDER BY`, and `LIMIT`
- calculated columns, KPIs, `COUNT`, `SUM`, `AVG`, `MIN`, and `MAX`
- `GROUP BY` and `HAVING`
- `INNER JOIN`, `LEFT JOIN`, self joins, and relationship checks
- subqueries, `EXISTS`, `NOT EXISTS`, and CTEs
- window functions: `ROW_NUMBER`, `DENSE_RANK`, `LAG`, running totals, and moving averages
- `CASE`, date functions, text functions, and `NULL` handling
- profiling, cleaning, deduplication, validation, reconciliation, and logs
- reporting views
- `EXPLAIN`, indexes, sargable date filters, and query tuning

## Suggested Project Brief

The MetroMart operations team wants a monthly retail performance report. They
suspect that some revenue is being overstated because cancelled/refunded orders,
returns, invalid item rows, product-name variants, and customer-quality issues
are mixed into the raw data.

Build a report that answers:

1. What are completed net sales, units, and order count by month, region, store,
   channel, department, category, and product?
2. Which products and categories are growing or shrinking month over month?
3. Which stores are above or below the company average for their region?
4. Which products have high return rates or low inventory?
5. Which customers have not purchased in the latest 45 days represented?
6. What data-quality issues would you fix before trusting the dashboard?

## Recommended Deliverables

- A short `README` that defines the business question, grain, filters, and assumptions
- A profiling section showing row counts, date ranges, NULLs, blanks, invalid values, and duplicates
- A cleaned reporting view that excludes invalid metric rows and handles returns deliberately
- KPI queries with clear result grain
- At least one CTE query and one window-function query
- At least one data-cleaning log or quality-test result
- One `EXPLAIN` before/after comparison for a date/status report

## Important Business Rules

- Treat `orders.status = 'completed'` as completed sales.
- Exclude item rows where `quantity` is `NULL` or less than or equal to zero.
- Exclude item rows where `unit_price` is `NULL` or negative.
- Net revenue should subtract valid refunds from valid gross completed revenue.
- Use `order_items.raw_product_name` for cleaning practice, but use
  `products.product_name` for trusted reporting after joining by `product_id`.
- Do not overwrite raw tables. Create views or clean tables when practicing
  cleaning workflows.
