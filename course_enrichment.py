"""Structured assessments and mini-projects appended to every course segment."""

ENRICHMENTS = [
    {
        "checks": [
            ("Which clause chooses the source table?", ["SELECT", "FROM", "WHERE"], 1, "FROM identifies the table that supplies rows."),
            ("Which filter includes prices of exactly 3.000?", ["price > 3.000", "price >= 3.000", "price <> 3.000"], 1, ">= means greater than or equal to."),
            ("How do you return the two highest prices?", ["ORDER BY price DESC LIMIT 2", "ORDER BY price ASC LIMIT 2", "LIMIT 2 ORDER BY price"], 0, "Descending order puts the highest values first, then LIMIT keeps two rows."),
        ],
        "project": ("Menu explorer", "The shop manager needs a short menu review before changing prices.",
            ["Return product name, category, and price for Coffee products.", "Sort most expensive first and keep the top three.", "Write one sentence explaining the result."],
            ["Uses explicit column names", "Filters category correctly", "Uses deterministic ORDER BY and LIMIT", "Result and written conclusion agree"],
            "SELECT product_name, category, price\nFROM products\nWHERE category = 'Coffee'\nORDER BY price DESC, product_name\nLIMIT 3;"),
    },
    {
        "checks": [
            ("What does a data type protect?", ["The browser theme", "The kind of value a column accepts", "The row order"], 1, "A column data type constrains the values stored in it."),
            ("Why name INSERT columns explicitly?", ["It documents value-to-column mapping", "It sorts the rows", "It creates an index"], 0, "An explicit column list makes the mapping clear and safer when schemas change."),
            ("Which type stores an exact course price?", ["DATE", "DECIMAL(6,3)", "VARCHAR(6)"], 1, "DECIMAL stores exact fixed-point numeric values."),
        ],
        "project": ("Build a suppliers table", "The shop needs a clean supplier directory that can be loaded repeatedly during practice.",
            ["Create suppliers with supplier_id, supplier_name, city, and active columns.", "Choose and explain suitable MySQL data types.", "Insert at least four rows and verify them with DESCRIBE and SELECT."],
            ["Script runs in coffee_shop", "Columns use appropriate types", "INSERT names its columns", "Verification statements are included"],
            "CREATE TABLE suppliers (\n  supplier_id INT,\n  supplier_name VARCHAR(100),\n  city VARCHAR(80),\n  active BOOLEAN\n);\n\nINSERT INTO suppliers (supplier_id, supplier_name, city, active) VALUES\n(1, 'North Roast', 'Kuwait City', TRUE),\n(2, 'Flour House', 'Hawalli', TRUE),\n(3, 'Tea Garden', 'Salmiya', TRUE),\n(4, 'Old Stock Co', 'Farwaniya', FALSE);\n\nDESCRIBE suppliers;\nSELECT * FROM suppliers;"),
    },
    {
        "checks": [
            ("What does COUNT(*) measure in orders?", ["Units", "Order rows", "Revenue"], 1, "COUNT(*) counts rows; SUM(quantity) counts units."),
            ("What is row revenue?", ["quantity + unit_price", "quantity * unit_price", "AVG(unit_price)"], 1, "Each line's revenue is its quantity multiplied by its sale price."),
            ("When does WHERE act?", ["Before an aggregate reads rows", "After ORDER BY", "Only during INSERT"], 0, "WHERE controls which detail rows participate in the calculation."),
        ],
        "project": ("Four-day sales snapshot", "An owner wants a defensible headline summary of the teaching dataset.",
            ["Calculate order rows, units, revenue, and average row revenue.", "Calculate Coffee revenue separately.", "State two findings and distinguish rows from units."],
            ["Expected totals are 10 rows, 21 units, and 45.800 revenue", "Coffee revenue is 30.500", "Aliases name metrics precisely", "Narrative does not call rows customer orders"],
            "SELECT COUNT(*) AS order_rows, SUM(quantity) AS units_sold,\n       SUM(quantity * unit_price) AS revenue,\n       ROUND(AVG(quantity * unit_price), 3) AS avg_row_revenue\nFROM orders;\n\nSELECT SUM(quantity * unit_price) AS coffee_revenue\nFROM orders WHERE category = 'Coffee';"),
    },
    {
        "checks": [
            ("What determines one output row in a grouped query?", ["The GROUP BY values", "The table name", "The LIMIT value"], 0, "Each distinct combination of grouping values becomes one result group."),
            ("Can units and revenue rank products differently?", ["No", "Yes, because prices differ", "Only with NULL dates"], 1, "Revenue combines quantity and price, so its ranking can differ from unit volume."),
            ("Which clause sorts grouped results?", ["ORDER BY", "WHERE", "FROM"], 0, "ORDER BY sorts the completed result rows."),
        ],
        "project": ("Category performance report", "Management needs one row per category for a weekly review.",
            ["Return category, order rows, units, and revenue.", "Sort by revenue descending with a stable tie-breaker.", "Identify the revenue leader and explain one difference between volume and revenue."],
            ["Grain is one row per category", "All metrics use the correct aggregate", "Sort is deterministic", "Interpretation matches output"],
            "SELECT category, COUNT(*) AS order_rows, SUM(quantity) AS units_sold,\n       SUM(quantity * unit_price) AS revenue\nFROM orders\nGROUP BY category\nORDER BY revenue DESC, category;"),
    },
    {
        "checks": [
            ("Which clause filters detail rows?", ["HAVING", "WHERE", "ORDER BY"], 1, "WHERE filters rows before groups are formed."),
            ("Which clause filters SUM(...) results?", ["HAVING", "FROM", "LIMIT"], 0, "HAVING filters completed groups and may use aggregate expressions."),
            ("Where should a date range normally go?", ["WHERE", "HAVING", "SELECT only"], 0, "A date condition should remove irrelevant detail rows before grouping."),
        ],
        "project": ("Meaningful category shortlist", "A campaign can include only categories with enough sales activity.",
            ["Summarize units and revenue by category for June 20–22.", "Keep categories with at least 4 units and revenue above 5.", "Explain why each condition belongs in WHERE or HAVING."],
            ["Date range is in WHERE", "Aggregate thresholds are in HAVING", "Grouping grain is correct", "Explanation describes logical order"],
            "SELECT category, SUM(quantity) AS units_sold,\n       SUM(quantity * unit_price) AS revenue\nFROM orders\nWHERE order_date BETWEEN '2026-06-20' AND '2026-06-22'\nGROUP BY category\nHAVING SUM(quantity) >= 4\n   AND SUM(quantity * unit_price) > 5\nORDER BY revenue DESC;"),
    },
    {
        "checks": [
            ("What does INNER JOIN exclude?", ["Matched rows", "Unmatched rows", "Selected columns"], 1, "INNER JOIN returns only rows satisfying the ON condition."),
            ("Which join preserves every left-table row?", ["LEFT JOIN", "INNER JOIN", "CROSS JOIN"], 0, "LEFT JOIN preserves all left rows and supplies NULLs when no match exists."),
            ("Where should table relationships be written?", ["ON", "LIMIT", "AS"], 0, "ON states how rows from the joined tables correspond."),
        ],
        "project": ("Catalog coverage audit", "The product manager wants sales totals and visibility for products that never sold.",
            ["Start from products and LEFT JOIN orders using the current product_name field.", "Return every product with units and revenue; show zero for missing sales.", "Add a second query that returns only products with no orders, then explain why names are a fragile relationship."],
            ["All products remain in the first result", "Join matches the fields available at this course stage", "COALESCE converts missing totals to zero", "Write-up recommends stable IDs for the later redesign"],
            "SELECT p.product_id, p.product_name,\n       COALESCE(SUM(o.quantity), 0) AS units_sold,\n       COALESCE(SUM(o.quantity * o.unit_price), 0) AS revenue\nFROM products p\nLEFT JOIN orders o ON o.product_name = p.product_name\nGROUP BY p.product_id, p.product_name;\n\nSELECT p.product_id, p.product_name\nFROM products p\nLEFT JOIN orders o ON o.product_name = p.product_name\nWHERE o.order_id IS NULL;\n-- This works for the teaching schema but names can change or collide.\n-- Segment 7 replaces this fragile relationship with product_id."),
    },
    {
        "checks": [
            ("What must a primary key be?", ["Unique and non-NULL", "Text only", "Repeated in every row"], 0, "A primary key uniquely and reliably identifies each row."),
            ("What does a foreign key protect?", ["Font selection", "Referential integrity", "Sort direction"], 1, "A foreign key prevents references to nonexistent parent keys."),
            ("Why retain order unit_price?", ["To preserve the historical sale price", "To replace product_id", "To count rows"], 0, "The current catalog price may change; the order must retain what was charged."),
        ],
        "project": ("Normalize a sales design", "A draft order table repeats product names and categories on every sale row.",
            ["Create products and order_items with primary and foreign keys.", "Keep historical unit_price in order_items.", "Insert valid sample rows and demonstrate that an invalid product reference is rejected."],
            ["Each table has a clear grain", "Keys and relationship are enforced", "Repeated product attributes are removed from order_items", "The expected failing statement is clearly labeled and not run with setup"],
            "CREATE TABLE products_norm (\n  product_id INT PRIMARY KEY, product_name VARCHAR(100) NOT NULL,\n  category VARCHAR(50) NOT NULL, current_price DECIMAL(8,3) NOT NULL\n);\nCREATE TABLE order_items_norm (\n  order_item_id INT PRIMARY KEY, product_id INT NOT NULL, quantity INT NOT NULL,\n  unit_price DECIMAL(8,3) NOT NULL, order_date DATE NOT NULL,\n  CONSTRAINT fk_item_product FOREIGN KEY (product_id) REFERENCES products_norm(product_id)\n);\n-- Expected to fail after setup: INSERT INTO order_items_norm VALUES (1, 999, 1, 2.000, '2026-06-24');"),
    },
    {
        "checks": [
            ("What can a scalar subquery return?", ["One value", "Any number of columns and rows", "Only table names"], 0, "A scalar subquery must produce a single value where one value is expected."),
            ("When is EXISTS useful?", ["Testing whether a match exists", "Renaming a column", "Sorting output"], 0, "EXISTS answers a yes/no matching question and can stop at the first match."),
            ("Why use a CTE?", ["To name and test an intermediate result", "To permanently store rows", "To create a password"], 0, "A CTE makes multi-step query logic readable and independently testable."),
        ],
        "project": ("Above-benchmark products", "A manager wants products whose revenue exceeds average product revenue.",
            ["Build product revenue in a CTE.", "Calculate the benchmark from that result.", "Return products above it with their revenue and the benchmark."],
            ["Aggregation occurs before the benchmark", "Benchmark is calculated from product totals", "Final result has one row per qualifying product", "CTE names communicate purpose"],
            "WITH product_sales AS (\n  SELECT p.product_id, p.product_name,\n         SUM(o.quantity * o.unit_price) AS revenue\n  FROM products p JOIN orders o ON o.product_id = p.product_id\n  GROUP BY p.product_id, p.product_name\n), benchmark AS (\n  SELECT AVG(revenue) AS avg_product_revenue FROM product_sales\n)\nSELECT ps.product_name, ps.revenue, b.avg_product_revenue\nFROM product_sales ps CROSS JOIN benchmark b\nWHERE ps.revenue > b.avg_product_revenue\nORDER BY ps.revenue DESC;"),
    },
    {
        "checks": [
            ("Do window functions normally collapse detail rows?", ["Yes", "No", "Only on Mondays"], 1, "Window functions attach analytical values while preserving the result grain."),
            ("What does PARTITION BY do?", ["Creates independent windows", "Deletes duplicates", "Limits output"], 0, "PARTITION BY restarts the window calculation for each partition."),
            ("Which function reads the previous row's value?", ["LEAD", "LAG", "RANK"], 1, "LAG accesses a value from an earlier row in the window order."),
        ],
        "project": ("Daily trend dashboard query", "The owner needs daily revenue, running revenue, prior-day revenue, and change.",
            ["Aggregate to one row per date in a CTE.", "Add a running total with an explicit ROWS frame.", "Use LAG for prior revenue and calculate daily change."],
            ["Final grain is one row per date", "Window order is deterministic", "Running frame is explicit", "First prior-day value is correctly NULL"],
            "WITH daily AS (\n  SELECT order_date, SUM(quantity * unit_price) AS revenue\n  FROM orders GROUP BY order_date\n)\nSELECT order_date, revenue,\n       SUM(revenue) OVER (ORDER BY order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_revenue,\n       LAG(revenue) OVER (ORDER BY order_date) AS prior_revenue,\n       revenue - LAG(revenue) OVER (ORDER BY order_date) AS revenue_change\nFROM daily ORDER BY order_date;"),
    },
    {
        "checks": [
            ("What does CASE produce?", ["A derived value based on conditions", "A new server", "An index automatically"], 0, "CASE maps conditions to output values inside a query."),
            ("Which function can replace NULL with a fallback?", ["COALESCE", "RANK", "DROP"], 0, "COALESCE returns the first non-NULL argument."),
            ("Why use an exclusive upper date bound for timestamps?", ["It safely includes the full prior period", "It sorts faster in every case", "Dates cannot use equality"], 0, "A half-open range avoids accidentally excluding times late on the final day."),
        ],
        "project": ("Presentation-ready sales labels", "A report needs consistent product labels, calendar fields, and revenue bands.",
            ["Create a cleaned uppercase product label.", "Return year, month, and weekday from order_date.", "Classify row revenue into low, medium, and high bands with CASE."],
            ["Text output is consistently formatted", "Date functions use order_date", "CASE conditions are ordered without overlap", "Aliases are report-friendly"],
            "SELECT UPPER(TRIM(p.product_name)) AS product_label,\n       YEAR(o.order_date) AS order_year, MONTH(o.order_date) AS order_month,\n       DAYNAME(o.order_date) AS weekday, o.quantity * o.unit_price AS row_revenue,\n       CASE WHEN o.quantity * o.unit_price >= 6 THEN 'High'\n            WHEN o.quantity * o.unit_price >= 3 THEN 'Medium' ELSE 'Low' END AS revenue_band\nFROM orders o JOIN products p ON p.product_id = o.product_id\nORDER BY o.order_id;"),
    },
    {
        "checks": [
            ("What should happen before UPDATE?", ["Preview affected rows with SELECT", "Delete the backup", "Disable constraints"], 0, "Previewing the same condition reduces the risk of changing unintended rows."),
            ("Why use a transaction for cleaning?", ["It supports validation before COMMIT", "It changes VARCHAR to DATE", "It removes every duplicate"], 0, "A transaction allows inspection and ROLLBACK before changes become permanent."),
            ("Are blank text and NULL identical?", ["Yes", "No", "Only in ORDER BY"], 1, "Blank text is a stored string; NULL represents a missing value."),
        ],
        "project": ("Safe product cleanup", "An imported staging table contains whitespace, blank categories, invalid prices, and duplicates.",
            ["Profile each issue with SELECT queries.", "Write documented cleaning rules and preview transformed values.", "Apply safe fixes inside a transaction, validate, then choose COMMIT or ROLLBACK."],
            ["Original problems are measured before changes", "Rules do not invent unknown business facts", "UPDATE conditions are narrow", "Validation occurs before transaction completion"],
            "SELECT COUNT(*) AS rows_total,\n       SUM(category IS NULL OR TRIM(category) = '') AS missing_category,\n       SUM(price <= 0 OR price IS NULL) AS invalid_price\nFROM products_staging;\nSELECT LOWER(TRIM(product_name)) AS normalized_name, COUNT(*)\nFROM products_staging GROUP BY normalized_name HAVING COUNT(*) > 1;\nSTART TRANSACTION;\nUPDATE products_staging SET product_name = TRIM(product_name)\nWHERE product_name <> TRIM(product_name);\nSELECT * FROM products_staging;\n-- COMMIT only after the validation queries pass; otherwise ROLLBACK;"),
    },
    {
        "checks": [
            ("Does a standard view store its result rows?", ["Usually no; it stores a query definition", "Always", "Only after ORDER BY"], 0, "A normal MySQL view saves query logic, not a separate result copy."),
            ("Why list view columns deliberately?", ["To provide a stable reporting interface", "To hide every row", "To create foreign keys"], 0, "Intentional columns make the view easier and safer for downstream consumers."),
            ("What should be checked after changing a view?", ["Dependent reports and results", "Only the font", "Nothing"], 0, "A view is an interface; changes can break or alter downstream reports."),
        ],
        "project": ("Trusted sales reporting view", "Two reports need the same product-level sales logic without duplicating joins and calculations.",
            ["Create a view with product identity, category, units, and revenue.", "Query the view for category totals and top products.", "Document grain, definitions, NULL behavior, and one limitation."],
            ["View has one documented row per product", "Join and aggregation are correct", "Downstream queries reuse the view", "Documentation states dependencies and limitations"],
            "CREATE OR REPLACE VIEW product_sales_v AS\nSELECT p.product_id, p.product_name, p.category,\n       COALESCE(SUM(o.quantity), 0) AS units_sold,\n       COALESCE(SUM(o.quantity * o.unit_price), 0) AS revenue\nFROM products p LEFT JOIN orders o ON o.product_id = p.product_id\nGROUP BY p.product_id, p.product_name, p.category;\n\nSELECT category, SUM(revenue) AS revenue\nFROM product_sales_v GROUP BY category ORDER BY revenue DESC;"),
    },
    {
        "checks": [
            ("What is EXPLAIN for?", ["Inspecting a query plan", "Formatting dates", "Committing a transaction"], 0, "EXPLAIN describes how MySQL intends to access and join data."),
            ("Why can wrapping an indexed date column in YEAR() hurt?", ["It may prevent an efficient range lookup", "YEAR deletes dates", "Indexes only support text"], 0, "A function on the indexed column can make the predicate non-sargable."),
            ("Is every index beneficial?", ["Yes", "No; indexes cost storage and write work", "Only primary keys cost space"], 1, "Indexes trade faster reads for storage and maintenance overhead."),
        ],
        "project": ("Query tuning report", "A monthly product sales report is slow on a large orders table.",
            ["Capture EXPLAIN before optimization.", "Rewrite the date filter as a half-open range and propose a justified composite index.", "Capture EXPLAIN after optimization and compare access type, key, and estimated rows."],
            ["Before/after query results are identical", "Index order follows filter/join needs", "Claims use EXPLAIN evidence", "Report discusses write and storage tradeoffs"],
            "EXPLAIN SELECT product_id, SUM(quantity * unit_price) AS revenue\nFROM orders\nWHERE order_date >= '2026-06-01' AND order_date < '2026-07-01'\nGROUP BY product_id;\n\nCREATE INDEX idx_orders_date_product ON orders(order_date, product_id);\n\nEXPLAIN SELECT product_id, SUM(quantity * unit_price) AS revenue\nFROM orders\nWHERE order_date >= '2026-06-01' AND order_date < '2026-07-01'\nGROUP BY product_id;"),
    },
]
