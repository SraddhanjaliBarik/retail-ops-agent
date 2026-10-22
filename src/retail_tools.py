
import os
import re

from dotenv import load_dotenv
from databricks import sql

load_dotenv()

HOST = os.getenv("DATABRICKS_HOST", "").removeprefix("https://").rstrip("/")
HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH", "")
TOKEN = os.getenv("DATABRICKS_TOKEN", "")
CATALOG = os.getenv("DATABRICKS_CATALOG", "retail_ops")


def query_databricks(query: str) -> list[dict]:
    """Run a read-only SQL query against Databricks."""

    query = query.strip().rstrip(";")

    if not re.match(r"^(SELECT|WITH)\b", query, re.IGNORECASE):
        raise ValueError("Only SELECT and WITH queries are allowed.")

    if ";" in query or "--" in query or "/*" in query:
        raise ValueError("Multiple SQL statements and comments are blocked.")

    blocked = re.compile(
        r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|"
        r"TRUNCATE|GRANT|REVOKE|CALL|EXECUTE)\b",
        re.IGNORECASE,
    )
    if blocked.search(query):
        raise ValueError("Write operations are not allowed.")

    if not HOST or not HTTP_PATH or not TOKEN:
        raise RuntimeError(
            "Configure DATABRICKS_HOST, DATABRICKS_HTTP_PATH "
            "and DATABRICKS_TOKEN in .env"
        )

    connection = sql.connect(
    server_hostname=HOST,
    http_path=HTTP_PATH,
    access_token=TOKEN,
    timeout=15,
    http_headers=[("User-Agent", "retail-ops-agent")],

    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            return [
                dict(zip(columns, row))
                for row in cursor.fetchmany(200)
            ]
    finally:
        connection.close()


def get_daily_sales(days: int = 7) -> list[dict]:
    """Retrieve the most recent daily sales KPIs."""

    if not 1 <= days <= 90:
        raise ValueError("days must be between 1 and 90")

    table = f"{CATALOG}.gold.daily_sales"
    return query_databricks(
        f"SELECT * FROM {table} "
        f"ORDER BY sales_date DESC LIMIT {days}"
    )


def get_revenue_anomalies(threshold: float = 2.0) -> list[dict]:
    """Find unusual revenue values using the Gold anomaly view."""

    if not 0.5 <= threshold <= 10:
        raise ValueError("threshold must be between 0.5 and 10")

    table = f"{CATALOG}.gold.revenue_anomalies"
    return query_databricks(
        f"SELECT * FROM {table} "
        f"WHERE ABS(z_score) >= {threshold} "
        "ORDER BY sales_date DESC LIMIT 50"
    )

def get_top_products(limit: int = 10) -> list[dict]:
    """Return products ranked by total revenue."""
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")

    table = f"{CATALOG}.gold.product_performance"
    return query_databricks(
        f"SELECT stockcode, description, units_sold, "
        f"total_revenue, total_orders FROM {table} "
        f"ORDER BY total_revenue DESC LIMIT {limit}"
    )

def get_country_sales(limit: int = 10) -> list[dict]:
    """Return countries ranked by total revenue."""

    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")

    table = f"{CATALOG}.gold.country_sales"

    return query_databricks(
        f"SELECT country, total_revenue, units_sold, "
        f"total_orders, unique_customers FROM {table} "
        f"ORDER BY total_revenue DESC LIMIT {limit}"
    )

def investigate_revenue_spike(sales_date: str = "2011-12-09") -> list[dict]:
    """Find the highest-revenue transaction lines for a sales date."""
    from datetime import date

    # Validate the date before using it in SQL.
    parsed_date = date.fromisoformat(sales_date)
    safe_date = parsed_date.isoformat()

    table = f"{CATALOG}.silver.orders_clean"

    query = f"""
        SELECT
            InvoiceNo,
            Description,
            Quantity,
            UnitPrice,
            ROUND(Quantity * UnitPrice, 2) AS line_revenue
        FROM {table}
        WHERE CAST(InvoiceDate AS DATE) = '{safe_date}'
        ORDER BY line_revenue DESC
        LIMIT 10
    """

    return query_databricks(query)

# --------------------------------------------------
# TRANSACTION VALIDATION TOOLS
# --------------------------------------------------

def get_customer_purchase_history(customer_id, limit=20):
    """
    Return recent invoices and purchase totals for a customer.
    """
    customer_id = int(customer_id)
    limit = max(1, min(int(limit), 100))

    query = f"""
        SELECT
            CustomerID,
            InvoiceNo,
            CAST(InvoiceDate AS DATE) AS invoice_date,
            COUNT(*) AS line_count,
            SUM(Quantity) AS total_units,
            ROUND(SUM(Quantity * UnitPrice), 2) AS invoice_revenue
        FROM retail_ops.silver.orders_clean
        WHERE CustomerID = {customer_id}
        GROUP BY
            CustomerID,
            InvoiceNo,
            CAST(InvoiceDate AS DATE)
        ORDER BY invoice_date DESC
        LIMIT {limit}
    """

    return query_databricks(query)


def get_product_sales_history(stock_code, limit=30):
    """
    Return recent daily sales history for a product.
    """
    # Escape single quotes to keep the SQL string safe.
    stock_code = str(stock_code).replace("'", "''")
    limit = max(1, min(int(limit), 100))

    query = f"""
        SELECT
            StockCode,
            Description,
            CAST(InvoiceDate AS DATE) AS sales_date,
            COUNT(DISTINCT InvoiceNo) AS invoice_count,
            SUM(Quantity) AS total_units,
            ROUND(SUM(Quantity * UnitPrice), 2) AS total_revenue,
            ROUND(AVG(UnitPrice), 2) AS average_unit_price
        FROM retail_ops.silver.orders_clean
        WHERE StockCode = '{stock_code}'
        GROUP BY
            StockCode,
            Description,
            CAST(InvoiceDate AS DATE)
        ORDER BY sales_date DESC
        LIMIT {limit}
    """

    return query_databricks(query)


def get_invoice_details(invoice_no):
    """
    Return transaction lines for a specific invoice.
    """
    invoice_no = str(invoice_no).replace("'", "''")

    query = f"""
        SELECT
            InvoiceNo,
            StockCode,
            Description,
            Quantity,
            UnitPrice,
            CustomerID,
            InvoiceDate,
            ROUND(Quantity * UnitPrice, 2) AS line_revenue
        FROM retail_ops.silver.orders_clean
        WHERE InvoiceNo = '{invoice_no}'
        ORDER BY line_revenue DESC
        LIMIT 200
    """

    return query_databricks(query)


def validate_invoice(invoice_no):
    """
    Summarize the lines and totals for an invoice.
    """
    invoice_no = str(invoice_no).replace("'", "''")

    query = f"""
        SELECT
            InvoiceNo,
            COUNT(*) AS line_count,
            COUNT(DISTINCT StockCode) AS distinct_products,
            SUM(Quantity) AS total_units,
            ROUND(SUM(Quantity * UnitPrice), 2) AS calculated_revenue,
            MIN(InvoiceDate) AS first_invoice_timestamp,
            MAX(InvoiceDate) AS last_invoice_timestamp,
            COUNT_IF(Quantity <= 0) AS non_positive_quantity_lines,
            COUNT_IF(UnitPrice < 0) AS negative_price_lines,
            COUNT_IF(UnitPrice = 0) AS zero_price_lines
        FROM retail_ops.silver.orders_clean
        WHERE InvoiceNo = '{invoice_no}'
        GROUP BY InvoiceNo
    """

    return query_databricks(query)

def get_product_quantity_outliers(stock_code, limit=20):
    """
    Compare invoice quantities for one product with its
    historical transaction quantities.
    """
    stock_code = str(stock_code).replace("'", "''")
    limit = max(1, min(int(limit), 100))

    query = f"""
        WITH invoice_quantities AS (
            SELECT
                StockCode,
                Description,
                InvoiceNo,
                CustomerID,
                CAST(InvoiceDate AS DATE) AS invoice_date,
                SUM(Quantity) AS invoice_quantity,
                ROUND(SUM(Quantity * UnitPrice), 2) AS invoice_revenue
            FROM retail_ops.silver.orders_clean
            WHERE StockCode = '{stock_code}'
              AND InvoiceNo NOT LIKE 'C%'
            GROUP BY
                StockCode,
                Description,
                InvoiceNo,
                CustomerID,
                CAST(InvoiceDate AS DATE)
        ),
        product_baseline AS (
            SELECT
                AVG(invoice_quantity) AS avg_quantity,
                STDDEV(invoice_quantity) AS std_quantity,
                percentile_approx(invoice_quantity, 0.5) AS median_quantity,
                COUNT(*) AS historical_invoice_count
            FROM invoice_quantities
        )
        SELECT
            q.StockCode,
            q.Description,
            q.InvoiceNo,
            q.CustomerID,
            q.invoice_date,
            q.invoice_quantity,
            q.invoice_revenue,
            b.avg_quantity,
            b.std_quantity,
            b.median_quantity,
            b.historical_invoice_count,
            CASE
                WHEN b.std_quantity > 0
                  THEN (q.invoice_quantity - b.avg_quantity)
                       / b.std_quantity
                ELSE NULL
            END AS quantity_z_score
        FROM invoice_quantities q
        CROSS JOIN product_baseline b
        ORDER BY q.invoice_quantity DESC
        LIMIT {limit}
    """

    return query_databricks(query)

def compare_invoice_quantity_with_all(invoice_no="581483", limit=20):
    """
    Compare the target invoice's total units with other invoices
    across the cleaned retail dataset.
    """
    invoice_no = str(invoice_no).replace("'", "''")
    limit = max(1, min(int(limit), 100))

    query = f"""
        WITH invoice_totals AS (
            SELECT
                InvoiceNo,
                CustomerID,
                CAST(InvoiceDate AS DATE) AS invoice_date,
                SUM(Quantity) AS total_units,
                ROUND(SUM(Quantity * UnitPrice), 2) AS total_revenue,
                COUNT(*) AS line_count
            FROM retail_ops.silver.orders_clean
            WHERE InvoiceNo NOT LIKE 'C%'
            GROUP BY
                InvoiceNo,
                CustomerID,
                CAST(InvoiceDate AS DATE)
        ),
        target AS (
            SELECT *
            FROM invoice_totals
            WHERE InvoiceNo = '{invoice_no}'
        ),
        population AS (
            SELECT
                COUNT(*) AS invoice_count,
                AVG(total_units) AS avg_units,
                STDDEV(total_units) AS std_units,
                percentile_approx(total_units, 0.5) AS median_units
            FROM invoice_totals
        )
        SELECT
            t.InvoiceNo AS target_invoice,
            t.invoice_date AS target_date,
            t.CustomerID AS target_customer,
            t.total_units AS target_units,
            t.total_revenue AS target_revenue,
            p.invoice_count AS comparison_invoice_count,
            p.avg_units AS average_invoice_units,
            p.std_units AS std_invoice_units,
            p.median_units AS median_invoice_units,
            CASE
                WHEN p.std_units > 0
                THEN (t.total_units - p.avg_units) / p.std_units
                ELSE NULL
            END AS quantity_z_score
        FROM target t
        CROSS JOIN population p
    """

    return query_databricks(query)
