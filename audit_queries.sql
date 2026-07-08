DROP DATABASE IF EXISTS course_audit;
CREATE DATABASE course_audit;
USE course_audit;

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(6,3) NOT NULL
);
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(6,3) NOT NULL,
    order_date DATE NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
INSERT INTO products (product_name, category, price) VALUES
('Iced Latte','Coffee',2.750),('Cold Brew','Coffee',3.000),('Croissant','Pastry',1.500),
('Brownie','Dessert',1.750),('Matcha Latte','Tea',2.900),('Americano','Coffee',1.250);
INSERT INTO orders (product_id, quantity, unit_price, order_date) VALUES
(1,2,2.750,'2026-06-20'),(2,1,3.000,'2026-06-20'),(3,3,1.500,'2026-06-20'),
(4,2,1.750,'2026-06-21'),(1,1,2.750,'2026-06-21'),(5,2,2.900,'2026-06-21'),
(6,4,1.250,'2026-06-22'),(2,2,3.000,'2026-06-22'),(3,1,1.500,'2026-06-22'),
(1,3,2.750,'2026-06-23');

SELECT SUM(quantity * unit_price) AS total_revenue FROM orders;
SELECT product_id, SUM(quantity * unit_price) AS revenue FROM orders GROUP BY product_id HAVING revenue >= 5 ORDER BY revenue DESC;
WITH product_sales AS (SELECT product_id, SUM(quantity * unit_price) revenue FROM orders GROUP BY product_id),
average_sales AS (SELECT AVG(revenue) average_product_revenue FROM product_sales)
SELECT p.product_name, ps.revenue FROM product_sales ps JOIN products p ON p.product_id=ps.product_id CROSS JOIN average_sales a WHERE ps.revenue>a.average_product_revenue;
WITH daily_sales AS (SELECT order_date, SUM(quantity*unit_price) daily_revenue FROM orders GROUP BY order_date)
SELECT order_date, daily_revenue, SUM(daily_revenue) OVER (ORDER BY order_date) running_revenue,
LAG(daily_revenue) OVER (ORDER BY order_date) previous_revenue FROM daily_sales;
SELECT product_name, price, CASE WHEN price>=3 THEN 'Premium' WHEN price>=2 THEN 'Standard' ELSE 'Value' END price_band FROM products;
SELECT DATE_FORMAT(order_date,'%W') weekday_name, SUM(quantity*unit_price) revenue FROM orders GROUP BY DATE_FORMAT(order_date,'%W');
SELECT UPPER(CONCAT(TRIM(product_name),' — ',TRIM(category))) product_label FROM products;
SELECT LOWER(TRIM(product_name)) normalized_name, COUNT(*) duplicate_count FROM products GROUP BY LOWER(TRIM(product_name)) HAVING COUNT(*)>1;
START TRANSACTION;
UPDATE products SET category='Coffee' WHERE LOWER(TRIM(category)) IN ('coffee','coffees');
ROLLBACK;
DROP TABLE IF EXISTS products_staging;
CREATE TABLE products_staging AS SELECT * FROM products;
ALTER TABLE products ADD CONSTRAINT chk_product_price_positive CHECK (price > 0);
CREATE OR REPLACE VIEW order_details AS
SELECT o.order_id,o.order_date,p.product_id,p.product_name,p.category,o.quantity,o.unit_price,o.quantity*o.unit_price revenue
FROM orders o JOIN products p ON p.product_id=o.product_id;
CREATE OR REPLACE VIEW product_sales AS
SELECT p.product_id,p.product_name,p.category,COALESCE(SUM(o.quantity),0) items_sold,COALESCE(SUM(o.quantity*o.unit_price),0) revenue
FROM products p LEFT JOIN orders o ON o.product_id=p.product_id GROUP BY p.product_id,p.product_name,p.category;
SELECT * FROM product_sales WHERE revenue>=6 ORDER BY revenue DESC;
EXPLAIN SELECT * FROM orders WHERE order_date='2026-06-22';
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_product_date ON orders(product_id,order_date);
SHOW INDEX FROM orders;
EXPLAIN SELECT order_id,quantity,unit_price FROM orders WHERE product_id=1 AND order_date>='2026-06-20';
DROP INDEX idx_orders_order_date ON orders;
