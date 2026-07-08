# Beginner setup — MySQL 8.0+

Use a local learning database. Do not run course reset scripts on an employer,
school, or production server.

## 1. Install the tools

Install MySQL Community Server 8.0 or newer and MySQL Workbench from the official
MySQL downloads page. During server installation, record the local username and
password you create. The examples assume the server is running on `localhost`
port `3306`.

You need two tools:

- **MySQL Server** stores and processes the data.
- **MySQL Workbench** is the graphical editor where you write and run SQL.

## 2. Test the connection

Open Workbench, select the local connection, enter the password, and run:

```sql
SELECT VERSION();
```

A row containing a version number confirms that the editor can reach the
server. If the connection fails, first confirm that the MySQL service is running
and that the host, port, username, and password match the installation.

## 3. Create the practice database

Open [`coffee_shop.sql`](coffee_shop.sql) in Workbench. Read the warning at the
top, select the entire script, and run it. The final results must show:

| table_name | row_count |
|---|---:|
| products | 6 |
| orders | 10 |

The second verification result must show `21` units and `45.800` revenue.

## 4. Reset when needed

Run `coffee_shop.sql` again. It deletes and recreates only the dedicated
`coffee_shop` practice database. Any work saved inside that database is removed,
so copy project queries to separate `.sql` files first.

## 5. How to run a lesson query

1. Run `USE coffee_shop;` once after opening a connection.
2. Paste or type the lesson query into a new SQL tab.
3. Select that statement and use Workbench's execute button.
4. Compare column names, row count, values, and sort order with the lesson.
5. Read the first error message if it fails; confirm spelling, quotes,
   punctuation, clause order, and the active database before changing the query.

## Data dictionary

### `products` — one row per menu product

| Column | Type | Meaning |
|---|---|---|
| `product_id` | `INT` | Unique product identifier |
| `product_name` | `VARCHAR(100)` | Display name used on the menu |
| `category` | `VARCHAR(50)` | Product reporting category |
| `price` | `DECIMAL(6,3)` | Current catalog price |

### `orders` — one row per product sale line

| Column | Type | Meaning |
|---|---|---|
| `order_id` | `INT` | Unique teaching row identifier |
| `product_name` | `VARCHAR(100)` | Product name captured on the sale line |
| `category` | `VARCHAR(50)` | Category captured on the sale line |
| `quantity` | `INT` | Units represented by the row |
| `unit_price` | `DECIMAL(6,3)` | Historical price charged per unit |
| `order_date` | `DATE` | Sale calendar date |

`COUNT(*)` on `orders` counts sale lines, not customers or complete receipts.
The small baseline table intentionally has no customer or receipt identifier.
The course therefore uses the precise term **order row** when interpreting it.
