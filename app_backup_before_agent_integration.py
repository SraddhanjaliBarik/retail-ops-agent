
import os
import re
import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from databricks_openai import DatabricksOpenAI

from src.retail_tools import (
    query_databricks,
    get_daily_sales,
    get_top_products,
    get_country_sales,
    get_customer_purchase_history,
    get_product_sales_history,
    get_invoice_details,
    validate_invoice,
)

load_dotenv()

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Retail Operations AI",
    page_icon="🛍️",
    layout="wide",
)

st.title("🛍️ Retail Operations AI")
st.caption(
    "Databricks · SQL · Python · Sales Analytics · AI-assisted investigation"
)

# --------------------------------------------------
# CONFIGURATION AND HELPERS
# --------------------------------------------------

MODEL_NAME = os.getenv(
    "DATABRICKS_MODEL",
    "databricks-meta-llama-3-3-70b-instruct",
)


def get_ai_client():
    """Create a Databricks model client."""
    return DatabricksOpenAI()


def to_dataframe(data):
    """Convert query results into a pandas DataFrame."""
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.DataFrame(data or [])


def safe_json(data):
    """Convert dates and other values into JSON-safe text."""
    return json.dumps(data, default=str, indent=2)


def format_currency(value):
    """Format a number as pounds sterling."""
    if pd.isna(value):
        return "£0.00"
    return f"£{float(value):,.2f}"


def find_column(df, candidates):
    """Find a column without depending on letter case."""
    lookup = {str(c).lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def require_date(value):
    """Accept only YYYY-MM-DD dates."""
    value = str(value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Date must use YYYY-MM-DD format.")
    date.fromisoformat(value)
    return value


# --------------------------------------------------
# LOAD DASHBOARD DATA
# --------------------------------------------------

@st.cache_data(ttl=300, show_spinner="Loading sales data from Databricks...")
def load_dashboard_data():
    daily = query_databricks("""
        SELECT *
        FROM retail_ops.gold.daily_sales
        ORDER BY sales_date
    """)

    countries = query_databricks("""
        SELECT *
        FROM retail_ops.gold.country_sales
        ORDER BY total_revenue DESC
    """)

    products = query_databricks("""
        SELECT *
        FROM retail_ops.gold.product_performance
        ORDER BY total_revenue DESC
        LIMIT 20
    """)

    return (
        to_dataframe(daily),
        to_dataframe(countries),
        to_dataframe(products),
    )


# --------------------------------------------------
# SALES ANOMALY DETECTION
# --------------------------------------------------

def detect_sales_anomalies(
    daily_df,
    window=7,
    threshold=2.0,
):
    """
    Compare each date's revenue with the preceding available
    dates. This is a screening rule, not proof of an error.
    """
    if daily_df.empty:
        return pd.DataFrame()

    date_col = find_column(daily_df, ["sales_date", "date"])
    revenue_col = find_column(
        daily_df, ["total_revenue", "revenue"]
    )

    if not date_col or not revenue_col:
        return pd.DataFrame()

    df = daily_df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df[revenue_col] = pd.to_numeric(
        df[revenue_col], errors="coerce"
    )
    df = df.dropna(subset=[date_col, revenue_col])
    df = df.sort_values(date_col).reset_index(drop=True)

    results = []

    for i, row in df.iterrows():
        previous = df.loc[
            max(0, i - window):i - 1, revenue_col
        ]

        baseline = previous.mean() if len(previous) else None
        stddev = (
            previous.std(ddof=1)
            if len(previous) >= 2
            else None
        )

        upper = (
            baseline + threshold * stddev
            if baseline is not None
            and pd.notna(stddev)
            else None
        )
        lower = (
            max(0, baseline - threshold * stddev)
            if baseline is not None
            and pd.notna(stddev)
            else None
        )

        if len(previous) < 2 or pd.isna(stddev):
            anomaly_type = "Insufficient history"
        elif row[revenue_col] > upper:
            anomaly_type = "Revenue spike"
        elif row[revenue_col] < lower:
            anomaly_type = "Revenue drop"
        else:
            anomaly_type = "Within baseline"

        results.append({
            "sales_date": row[date_col].date(),
            "total_revenue": row[revenue_col],
            "baseline_revenue": baseline,
            "upper_limit": upper,
            "lower_limit": lower,
            "anomaly_type": anomaly_type,
        })

    return pd.DataFrame(results)


# --------------------------------------------------
# MULTI-TOOL REVENUE INVESTIGATION
# --------------------------------------------------

def investigate_revenue_spike(sales_date):
    """
    Gather daily comparison, largest transactions,
    invoice validation, customer history and product history.
    """
    sales_date = require_date(sales_date)

    daily_query = f"""
        SELECT
            sales_date,
            total_revenue,
            units_sold,
            total_orders,
            unique_customers
        FROM retail_ops.gold.daily_sales
        WHERE sales_date BETWEEN
            DATE_SUB(DATE('{sales_date}'), 1)
            AND DATE('{sales_date}')
        ORDER BY sales_date
    """
    daily_comparison = query_databricks(daily_query)

    transaction_query = f"""
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
        WHERE CAST(InvoiceDate AS DATE) = DATE('{sales_date}')
        ORDER BY line_revenue DESC
        LIMIT 10
    """
    transactions = query_databricks(transaction_query)

    evidence = {
        "investigation_date": sales_date,
        "daily_comparison": daily_comparison,
        "largest_transactions": transactions,
        "validation_evidence": {},
        "notes": [
            "Evidence comes from the cleaned Silver table and Gold summaries.",
            "A statistical anomaly is not automatically a data error.",
            "The original source has not been independently verified.",
        ],
    }

    if not transactions:
        evidence["notes"].append(
            "No transaction lines were found for this date."
        )
        return evidence

    largest = transactions[0]
    invoice_no = largest.get("InvoiceNo")
    customer_id = largest.get("CustomerID")
    stock_code = largest.get("StockCode")

    validation = {
        "largest_transaction": largest,
        "invoice_validation": validate_invoice(invoice_no),
        "invoice_lines": get_invoice_details(invoice_no),
        "customer_history": (
            get_customer_purchase_history(customer_id, limit=10)
            if customer_id is not None
            else []
        ),
        "product_history": get_product_sales_history(
            stock_code, limit=10
        ),
    }

    evidence["validation_evidence"] = validation
    return evidence


# --------------------------------------------------
# AI INVESTIGATION AND CHAT
# --------------------------------------------------

def answer_with_ai(question, evidence):
    """Ask the Databricks model to explain supplied SQL evidence."""
    client = get_ai_client()

    system_prompt = """
You are a retail operations analytics assistant.

Rules:
1. Base factual claims only on the evidence provided.
2. Use GBP (£) when discussing revenue.
3. Do not invent causes, transactions, customers, or figures.
4. Distinguish confirmed observations from hypotheses.
5. Explain the relevant dates, quantities, invoice totals and comparisons.
6. If evidence is insufficient, say what remains to be checked.
7. A successful SQL validation does not prove that an order is legitimate.
8. Do not claim you checked the original source unless the evidence says so.
9. Give a clear, professional answer suitable for a business analyst.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"SQL evidence:\n{safe_json(evidence)}"
                ),
            },
        ],
        temperature=0.1,
        max_tokens=1200,
    )

    return response.choices[0].message.content


def get_chat_evidence(question):
    """Choose evidence queries based on the user's question."""
    q = question.lower()

    # Investigate a date if the question includes YYYY-MM-DD.
    match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", question)

    if any(word in q for word in [
        "anomaly", "spike", "unusual", "investigate",
        "why did revenue", "revenue increase",
    ]):
        sales_date = match.group(0) if match else "2011-12-09"
        return investigate_revenue_spike(sales_date)

    if "invoice" in q or "transaction" in q:
        invoice_match = re.search(
            r"\b(?:invoice\s*)?(\d{6})\b",
            question,
            flags=re.IGNORECASE,
        )
        invoice_no = invoice_match.group(1) if invoice_match else "581483"
        return {
            "invoice_validation": validate_invoice(invoice_no),
            "invoice_lines": get_invoice_details(invoice_no),
        }

    if "customer" in q:
        customer_match = re.search(r"\b(\d{4,})\b", question)
        customer_id = int(customer_match.group(1)) if customer_match else 16446
        return {
            "customer_id": customer_id,
            "purchase_history": get_customer_purchase_history(
                customer_id, limit=10
            ),
        }

    if "product" in q or "stockcode" in q or "stock code" in q:
        product_match = re.search(
            r"\b(?:stock\s*code\s*)?([A-Za-z0-9]{2,})\b",
            question,
            flags=re.IGNORECASE,
        )
        stock_code = product_match.group(1) if product_match else "23843"

        if stock_code.lower() in {
            "product", "products", "history", "sales"
        }:
            stock_code = "23843"

        return {
            "stock_code": stock_code,
            "product_history": get_product_sales_history(
                stock_code, limit=10
            ),
        }

    if "country" in q:
        return {"country_sales": get_country_sales(10)}

    if any(word in q for word in [
        "sales", "revenue", "orders", "daily",
    ]):
        return {"recent_daily_sales": get_daily_sales(7)}

    return {
        "recent_daily_sales": get_daily_sales(7),
        "top_products": get_top_products(10),
        "country_sales": get_country_sales(10),
    }


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.header("Project information")
    st.write("**Platform:** Databricks")
    st.write("**Language:** Python and SQL")
    st.write("**Data layer:** Silver and Gold")
    st.write("**AI:** Databricks model endpoint")

    st.divider()

    if st.button("🔄 Refresh dashboard data", use_container_width=True):
        load_dashboard_data.clear()
        st.rerun()

    if st.button("🧹 Clear chat history", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.caption(
        "Anomaly detection is an exploratory statistical check. "
        "Always validate important findings against source records."
    )


# --------------------------------------------------
# LOAD AND PREPARE DATA
# --------------------------------------------------

try:
    daily_df, country_df, product_df = load_dashboard_data()
except Exception as exc:
    st.error("Could not load data from Databricks.")
    st.exception(exc)
    st.info(
        "Check your .env settings, SQL warehouse HTTP path, "
        "permissions, and certificate environment variables."
    )
    st.stop()

if daily_df.empty:
    st.warning("The Gold daily sales table has no records.")
    st.stop()

date_col = find_column(daily_df, ["sales_date", "date"])
revenue_col = find_column(
    daily_df, ["total_revenue", "revenue"]
)
units_col = find_column(daily_df, ["units_sold", "total_units"])
orders_col = find_column(daily_df, ["total_orders", "order_count"])
customers_col = find_column(
    daily_df, ["unique_customers", "customer_count"]
)

if not date_col or not revenue_col:
    st.error(
        "The daily sales table must contain sales_date and total_revenue columns."
    )
    st.write("Columns returned:", list(daily_df.columns))
    st.stop()

daily_df[date_col] = pd.to_datetime(
    daily_df[date_col], errors="coerce"
)
daily_df[revenue_col] = pd.to_numeric(
    daily_df[revenue_col], errors="coerce"
)
daily_df = daily_df.dropna(subset=[date_col, revenue_col])
daily_df = daily_df.sort_values(date_col)

# --------------------------------------------------
# DATE FILTER
# --------------------------------------------------

st.subheader("Sales dashboard")

min_date = daily_df[date_col].min().date()
max_date = daily_df[date_col].max().date()

default_start = max(min_date, max_date - timedelta(days=30))

col_start, col_end = st.columns(2)

with col_start:
    start_date = st.date_input(
        "Start date",
        value=default_start,
        min_value=min_date,
        max_value=max_date,
    )

with col_end:
    end_date = st.date_input(
        "End date",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )

if start_date > end_date:
    st.error("Start date must be on or before the end date.")
    st.stop()

filtered_df = daily_df[
    (daily_df[date_col].dt.date >= start_date)
    & (daily_df[date_col].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning("No sales records exist for this date range.")
    st.stop()

# --------------------------------------------------
# KPI SUMMARY
# --------------------------------------------------

total_revenue = filtered_df[revenue_col].sum()

total_units = (
    pd.to_numeric(filtered_df[units_col], errors="coerce").sum()
    if units_col
    else 0
)

total_orders = (
    pd.to_numeric(filtered_df[orders_col], errors="coerce").sum()
    if orders_col
    else 0
)

# Daily unique-customer counts cannot be summed to obtain
# the distinct customer count for the whole selected period.
customer_days = (
    pd.to_numeric(filtered_df[customers_col], errors="coerce").sum()
    if customers_col
    else 0
)

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total revenue", format_currency(total_revenue))
k2.metric("Units sold", f"{total_units:,.0f}")
k3.metric("Orders (daily total)", f"{total_orders:,.0f}")
k4.metric("Customer-days", f"{customer_days:,.0f}")

st.caption(
    "Customer-days is the sum of daily unique-customer counts; "
    "it is not the distinct customer count for the whole period. "
    "Daily order counts are summed across dates."
)

# --------------------------------------------------
# DAILY SALES TREND
# --------------------------------------------------

st.subheader("Daily revenue trend")

trend_df = filtered_df.set_index(date_col)[[revenue_col]]
st.line_chart(trend_df, y=revenue_col)

with st.expander("View daily sales data"):
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# --------------------------------------------------
# AUTOMATIC ANOMALY DETECTION
# --------------------------------------------------

st.subheader("Revenue anomaly detection")

anomalies = detect_sales_anomalies(daily_df)

if not anomalies.empty:
    selected_anomalies = anomalies[
        (pd.to_datetime(anomalies["sales_date"]).dt.date >= start_date)
        & (pd.to_datetime(anomalies["sales_date"]).dt.date <= end_date)
    ].copy()

    flagged = selected_anomalies[
        selected_anomalies["anomaly_type"].isin(
            ["Revenue spike", "Revenue drop"]
        )
    ]

    if not flagged.empty:
        st.warning(
            f"{len(flagged)} date(s) exceeded the exploratory "
            "historical revenue thresholds."
        )
    else:
        st.info("No revenue spikes or drops were detected in this range.")

    st.dataframe(
        selected_anomalies,
        use_container_width=True,
        hide_index=True,
    )

    if not flagged.empty:
        flagged["sales_date"] = pd.to_datetime(
            flagged["sales_date"]
        ).dt.date

        anomaly_dates = flagged["sales_date"].tolist()

        selected_date = st.selectbox(
            "Choose a flagged date to investigate",
            options=anomaly_dates,
            format_func=lambda d: d.strftime("%Y-%m-%d"),
        )

        if st.button(
            "🔎 Investigate selected date",
            type="primary",
        ):
            with st.spinner(
                "Querying Databricks and validating transaction evidence..."
            ):
                try:
                    evidence = investigate_revenue_spike(
                        selected_date.isoformat()
                    )
                    question = (
                        f"Investigate the revenue anomaly on "
                        f"{selected_date.isoformat()}. Compare the date "
                        "with the previous day, validate the largest "
                        "transaction, and examine customer and product "
                        "history. Separate facts from hypotheses."
                    )
                    answer = answer_with_ai(question, evidence)

                    st.session_state["last_investigation"] = {
                        "question": question,
                        "evidence": evidence,
                        "answer": answer,
                    }
                except Exception as exc:
                    st.error("The investigation failed.")
                    st.exception(exc)

if "last_investigation" in st.session_state:
    result = st.session_state["last_investigation"]

    with st.expander("Latest investigation evidence", expanded=True):
        st.markdown("**AI interpretation**")
        st.write(result["answer"])

        st.markdown("**SQL evidence returned**")
        st.json(result["evidence"])


# --------------------------------------------------
# COUNTRY SALES
# --------------------------------------------------

st.subheader("Sales by country")

if not country_df.empty:
    country_name_col = find_column(country_df, ["Country", "country"])
    country_revenue_col = find_column(
        country_df, ["total_revenue", "revenue"]
    )

    if country_name_col and country_revenue_col:
        country_plot = country_df.copy()
        country_plot[country_revenue_col] = pd.to_numeric(
            country_plot[country_revenue_col], errors="coerce"
        )
        country_plot = country_plot.dropna(
            subset=[country_revenue_col]
        )
        country_plot = country_plot.sort_values(
            country_revenue_col, ascending=False
        ).head(10)

        st.bar_chart(
            country_plot.set_index(country_name_col)[
                country_revenue_col
            ]
        )
        st.dataframe(
            country_plot,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning(
            "Could not identify country and revenue columns. "
            f"Columns: {list(country_df.columns)}"
        )
else:
    st.info("No country sales data was returned.")

# --------------------------------------------------
# PRODUCT PERFORMANCE
# --------------------------------------------------

st.subheader("Top product performance")

if not product_df.empty:
    product_name_col = find_column(
        product_df, ["Description", "product_name", "Product"]
    )
    product_revenue_col = find_column(
        product_df, ["total_revenue", "revenue"]
    )

    if product_name_col and product_revenue_col:
        product_plot = product_df.copy()
        product_plot[product_revenue_col] = pd.to_numeric(
            product_plot[product_revenue_col], errors="coerce"
        )
        product_plot = product_plot.dropna(
            subset=[product_revenue_col]
        )
        product_plot = product_plot.sort_values(
            product_revenue_col, ascending=False
        ).head(10)

        st.bar_chart(
            product_plot.set_index(product_name_col)[
                product_revenue_col
            ]
        )
        st.dataframe(
            product_plot,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning(
            "Could not identify product and revenue columns. "
            f"Columns: {list(product_df.columns)}"
        )
else:
    st.info("No product performance data was returned.")

# --------------------------------------------------
# AI CHAT
# --------------------------------------------------

st.divider()
st.subheader("💬 Ask the Retail Operations AI")
st.write(
    "Ask about revenue, sales trends, products, countries, customers, "
    "invoices, or anomalies. The assistant retrieves relevant data "
    "from Databricks before generating its answer."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input(
    "Example: Why did revenue spike on 2011-12-09?"
)

if question:
    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(
            "Retrieving evidence from Databricks and generating an answer..."
        ):
            try:
                evidence = get_chat_evidence(question)
                response = answer_with_ai(question, evidence)
                st.markdown(response)

                with st.expander("Evidence used for this answer"):
                    st.json(evidence)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                })

            except Exception as exc:
                error_message = (
                    "I could not complete that request. "
                    "Check the Databricks connection, SQL query, and "
                    "model endpoint configuration."
                )
                st.error(error_message)
                st.exception(exc)

st.divider()
st.caption(
    "Retail Operations AI · Portfolio project · "
    "Python + Databricks SQL + Streamlit + AI"
)
