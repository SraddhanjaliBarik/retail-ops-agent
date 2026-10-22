
from datetime import date

import pandas as pd
import streamlit as st

from src.retail_tools import query_databricks
from src.agent import ask_agent


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Retail Operations AI",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONSTANTS
# ============================================================

DAILY_TABLE = "retail_ops.gold.daily_sales"
COUNTRY_TABLE = "retail_ops.gold.country_sales"
PRODUCT_TABLE = "retail_ops.gold.product_performance"
SILVER_TABLE = "retail_ops.silver.orders_clean"

st.title("🛍️ Retail Operations Intelligence")
st.caption(
    "Databricks Lakehouse · SQL Analytics · AI Agent · Data Quality"
)


# ============================================================
# DATA ACCESS HELPERS
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_table(sql: str) -> pd.DataFrame:
    """Run SQL through the project's existing Databricks helper."""
    result = query_databricks(sql)

    if isinstance(result, pd.DataFrame):
        return result.copy()

    if result is None:
        return pd.DataFrame()

    if isinstance(result, dict):
        return pd.DataFrame([result])

    if isinstance(result, list):
        return pd.DataFrame(result)

    try:
        return pd.DataFrame(result)
    except Exception as exc:
        raise TypeError(
            "query_databricks() returned an unsupported result."
        ) from exc


def find_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    """Find a column without depending on capitalization."""
    lookup = {str(col).lower(): col for col in df.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def to_numeric(
    df: pd.DataFrame,
    candidates: list[str],
) -> pd.Series:
    """Return a numeric series, or zeros if the column is missing."""
    column = find_column(df, candidates)

    if column is None:
        return pd.Series(0, index=df.index, dtype="float64")

    return pd.to_numeric(df[column], errors="coerce").fillna(0)


def format_currency(value: float) -> str:
    return f"£{value:,.2f}"


def show_missing_column_message(
    table_name: str,
    df: pd.DataFrame,
) -> None:
    st.warning(
        f"Expected columns were not found in {table_name}. "
        f"Returned columns: {', '.join(map(str, df.columns)) or 'none'}"
    )


def normalize_result(result) -> pd.DataFrame:
    """Normalize SQL/tool results to a DataFrame."""
    if isinstance(result, pd.DataFrame):
        return result.copy()

    if result is None:
        return pd.DataFrame()

    if isinstance(result, dict):
        return pd.DataFrame([result])

    if isinstance(result, list):
        # Handle a list containing a single result wrapper.
        if len(result) == 1 and isinstance(result[0], dict):
            first = result[0]
            if "result" in first and isinstance(first["result"], list):
                return pd.DataFrame(first["result"])
        return pd.DataFrame(result)

    return pd.DataFrame(result)


def load_spike_lines(selected_date: date) -> pd.DataFrame:
    """
    Return the highest-revenue invoice/product groups for one date.

    The selected date comes from Streamlit's date picker, and is
    converted to ISO format before being inserted into the query.
    """
    safe_date = selected_date.isoformat()

    sql = f"""
        SELECT
            InvoiceNo,
            Description,
            Quantity AS total_units,
            UnitPrice AS unit_price,
            ROUND(Quantity * UnitPrice, 2) AS line_revenue
        FROM {SILVER_TABLE}
        WHERE CAST(InvoiceDate AS DATE) = '{safe_date}'
        ORDER BY line_revenue DESC
        LIMIT 10
    """

    return normalize_result(query_databricks(sql))


def show_spike_charts(selected_date: date) -> None:
    """Render transaction charts and supporting evidence."""
    with st.spinner("Loading transaction evidence from Databricks..."):
        spike_df = load_spike_lines(selected_date)

    if spike_df.empty:
        st.info(f"No transaction lines found for {selected_date}.")
        return

    required = [
        "InvoiceNo",
        "Description",
        "total_units",
        "unit_price",
        "line_revenue",
    ]

    missing = [col for col in required if col not in spike_df.columns]

    if missing:
        st.warning(
            "The transaction query returned an unexpected schema. "
            f"Missing columns: {', '.join(missing)}"
        )
        st.dataframe(spike_df, hide_index=True, width="stretch")
        return

    spike_df["total_units"] = pd.to_numeric(
        spike_df["total_units"], errors="coerce"
    ).fillna(0)

    spike_df["unit_price"] = pd.to_numeric(
        spike_df["unit_price"], errors="coerce"
    ).fillna(0)

    spike_df["line_revenue"] = pd.to_numeric(
        spike_df["line_revenue"], errors="coerce"
    ).fillna(0)

    spike_df = spike_df.sort_values(
        "line_revenue", ascending=False
    ).reset_index(drop=True)

    top_line = spike_df.iloc[0]

    st.markdown(f"#### Highest-revenue lines on {selected_date.isoformat()}")

    k1, k2, k3 = st.columns(3)

    k1.metric(
        "Largest line revenue",
        format_currency(float(top_line["line_revenue"])),
    )

    k2.metric(
        "Units on largest line",
        f"{float(top_line['total_units']):,.0f}",
    )

    k3.metric(
        "Invoice",
        str(top_line["InvoiceNo"]),
    )

    # Chart 1: Revenue by invoice/product.
    chart_df = spike_df.copy()
    chart_df["chart_label"] = (
        "Invoice "
        + chart_df["InvoiceNo"].astype(str)
        + " · "
        + chart_df["Description"].astype(str).str.slice(0, 35)
    )

    st.markdown("#### 1. Revenue by transaction line")

    revenue_chart = chart_df[
        ["chart_label", "line_revenue"]
    ].set_index("chart_label")

    st.bar_chart(
        revenue_chart,
        x_label="Invoice and product",
        y_label="Revenue (£)",
        horizontal=True,
        width="stretch",
    )

    # Chart 2: Quantity by invoice/product.
    st.markdown("#### 2. Quantity by transaction line")

    quantity_chart = chart_df[
        ["chart_label", "total_units"]
    ].set_index("chart_label")

    st.bar_chart(
        quantity_chart,
        x_label="Invoice and product",
        y_label="Units",
        horizontal=True,
        width="stretch",
    )

    # Chart 3: Unit price by invoice/product.
    st.markdown("#### 3. Unit price comparison")

    price_chart = chart_df[
        ["chart_label", "unit_price"]
    ].set_index("chart_label")

    st.bar_chart(
        price_chart,
        x_label="Invoice and product",
        y_label="Unit price (£)",
        horizontal=True,
        width="stretch",
    )

    st.markdown("#### Transaction evidence")

    evidence_df = spike_df.rename(
        columns={
            "InvoiceNo": "Invoice",
            "Description": "Product",
            "total_units": "Units",
            "unit_price": "Unit price (£)",
            "line_revenue": "Line revenue (£)",
        }
    )

    st.dataframe(
        evidence_df,
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "This table shows the ten highest-revenue individual invoice "
        "lines for the selected date. It is not a complete breakdown "
        "of every sale on that date. A statistical outlier alone does "
        "not establish fraud, a data error, or the reason for a spike."
    )


# ============================================================
# SIDEBAR CONTROLS
# ============================================================

with st.sidebar:
    st.header("Dashboard controls")
    st.caption("Dashboard tables are cached for 5 minutes.")

    if st.button("🔄 Refresh data", width="stretch"):
        st.cache_data.clear()
        st.rerun()


# ============================================================
# LOAD GOLD TABLES
# ============================================================

try:
    with st.spinner("Loading Gold tables from Databricks..."):
        daily_df = load_table(
            f"SELECT * FROM {DAILY_TABLE} ORDER BY sales_date"
        )
        country_df = load_table(
            f"SELECT * FROM {COUNTRY_TABLE}"
        )
        product_df = load_table(
            f"SELECT * FROM {PRODUCT_TABLE}"
        )

except Exception as exc:
    st.error("Unable to load the Databricks Gold tables.")
    st.info(
        "Check your SQL warehouse, credentials, and Gold table names."
    )
    with st.expander("Technical error"):
        st.exception(exc)
    st.stop()


if daily_df.empty:
    st.warning(f"The daily sales table {DAILY_TABLE} returned no rows.")
    st.stop()


# ============================================================
# NORMALIZE DAILY SALES COLUMNS
# ============================================================

date_col = find_column(
    daily_df,
    ["sales_date", "date", "order_date", "invoicedate"],
)

revenue_col = find_column(
    daily_df,
    ["total_revenue", "revenue", "daily_revenue", "total_sales"],
)

quantity_col = find_column(
    daily_df,
    ["total_quantity", "quantity", "total_units", "units_sold"],
)

orders_col = find_column(
    daily_df,
    ["total_orders", "orders", "order_count", "invoice_count"],
)

customers_col = find_column(
    daily_df,
    ["unique_customers", "customer_count", "customers"],
)

if date_col is None or revenue_col is None:
    show_missing_column_message(DAILY_TABLE, daily_df)
    st.stop()


daily_df[date_col] = pd.to_datetime(
    daily_df[date_col],
    errors="coerce",
).dt.date

daily_df = daily_df.dropna(subset=[date_col]).copy()

daily_df[revenue_col] = pd.to_numeric(
    daily_df[revenue_col],
    errors="coerce",
)

daily_df = daily_df.dropna(subset=[revenue_col]).copy()

if daily_df.empty:
    st.error("No valid dates or revenue values were found.")
    st.stop()


# ============================================================
# DATE FILTER
# ============================================================

min_date = min(daily_df[date_col])
max_date = max(daily_df[date_col])

with st.sidebar:
    st.subheader("Dashboard date range")

    selected_dates = st.date_input(
        "Choose a period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="dashboard_date_range",
    )

if isinstance(selected_dates, (tuple, list)):
    if len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif len(selected_dates) == 1:
        start_date = end_date = selected_dates[0]
    else:
        start_date, end_date = min_date, max_date
else:
    start_date = end_date = selected_dates

if start_date > end_date:
    st.warning("Start date is after end date. The dates have been swapped.")
    start_date, end_date = end_date, start_date

filtered_daily = daily_df[
    daily_df[date_col].between(start_date, end_date)
].copy()

if filtered_daily.empty:
    st.warning("No daily sales were found for the selected date range.")
    st.stop()


# ============================================================
# BUSINESS OVERVIEW
# ============================================================

total_revenue = float(filtered_daily[revenue_col].sum())

total_units = (
    float(to_numeric(filtered_daily, [quantity_col]).sum())
    if quantity_col
    else 0.0
)

total_orders = (
    float(to_numeric(filtered_daily, [orders_col]).sum())
    if orders_col
    else None
)

customer_days = (
    float(to_numeric(filtered_daily, [customers_col]).sum())
    if customers_col
    else None
)

st.subheader("Business overview")

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total revenue", format_currency(total_revenue))
k2.metric("Units sold", f"{total_units:,.0f}")

k3.metric(
    "Orders / invoices",
    f"{total_orders:,.0f}" if total_orders is not None else "Not available",
)

k4.metric(
    "Customer-days*",
    f"{customer_days:,.0f}" if customer_days is not None else "Not available",
)

st.caption(
    "*Customer-days sums daily unique-customer counts, if that is how "
    "the Gold table is defined. It may not equal distinct customers "
    "across the entire selected period."
)


# ============================================================
# DAILY REVENUE TREND
# ============================================================

st.divider()
st.subheader("📈 Daily revenue trend")

trend_df = filtered_daily[[date_col, revenue_col]].copy()
trend_df = trend_df.sort_values(date_col).set_index(date_col)

st.line_chart(
    trend_df[[revenue_col]],
    x_label="Date",
    y_label="Revenue (£)",
    width="stretch",
)


# ============================================================
# REVENUE ANOMALY SCREENING
# ============================================================

st.divider()
st.subheader("🔎 Revenue anomaly screening")

anomaly_df = filtered_daily.copy()
valid_revenue = anomaly_df[revenue_col].dropna()

if len(valid_revenue) >= 3 and valid_revenue.std(ddof=0) > 0:
    mean_revenue = valid_revenue.mean()
    std_revenue = valid_revenue.std(ddof=0)

    anomaly_df["revenue_z_score"] = (
        anomaly_df[revenue_col] - mean_revenue
    ) / std_revenue

    unusual_df = anomaly_df[
        anomaly_df["revenue_z_score"].abs() >= 2
    ].copy()

    unusual_df = unusual_df.sort_values(
        "revenue_z_score",
        key=lambda values: values.abs(),
        ascending=False,
    )

    if unusual_df.empty:
        st.success(
            "No daily revenue values exceeded an absolute z-score of 2 "
            "in the selected period."
        )
    else:
        st.warning(
            f"Found {len(unusual_df)} potentially unusual day(s). "
            "These are statistical flags, not proof of fraud or error."
        )

        display_columns = [date_col, revenue_col, "revenue_z_score"]

        if quantity_col:
            display_columns.append(quantity_col)

        st.dataframe(
            unusual_df[display_columns],
            width="stretch",
            hide_index=True,
        )

        investigation_date = st.selectbox(
            "Choose a date to investigate",
            options=unusual_df[date_col].tolist(),
            format_func=lambda value: value.isoformat(),
            key="investigation_date",
        )

        if st.button(
            "🔍 Investigate selected date with AI",
            type="primary",
            key="investigate_with_agent",
        ):
            question = (
                f"Investigate the revenue on {investigation_date}. "
                "Examine the largest transactions and available customer "
                "and product history. Validate relevant invoices if the "
                "available tools support it. Clearly distinguish verified "
                "facts from hypotheses. Do not infer fraud from an outlier."
            )

            with st.spinner("Investigating with the AI agent..."):
                try:
                    result = ask_agent(question)

                    if isinstance(result, dict):
                        answer = result.get(
                            "answer",
                            "The agent returned no answer.",
                        )
                        evidence = result.get("evidence", [])
                    else:
                        answer = str(result)
                        evidence = []

                    st.markdown("### AI investigation result")
                    st.markdown(answer)

                    with st.expander("Raw Databricks evidence"):
                        st.json(evidence)

                except Exception as exc:
                    st.error("The AI investigation could not be completed.")
                    st.exception(exc)

else:
    st.info(
        "At least three daily revenue values with non-zero variance "
        "are needed for this z-score screening."
    )


# ============================================================
# DEDICATED TRANSACTION-LEVEL SPIKE CHARTS
# ============================================================

st.divider()
st.subheader("📊 Transaction-level revenue investigation")

st.write(
    "Inspect the highest-revenue invoice lines for a selected date. "
    "This view queries the Silver table directly."
)

default_spike_date = date(2011, 12, 9)

spike_date = st.date_input(
    "Investigation date",
    value=default_spike_date,
    key="transaction_spike_date",
)

if st.button(
    "Load transaction charts",
    type="primary",
    key="load_transaction_charts",
):
    st.session_state["show_transaction_charts"] = True
    st.session_state["loaded_spike_date"] = spike_date

if st.session_state.get("show_transaction_charts", False):
    chart_date = st.session_state.get(
        "loaded_spike_date",
        default_spike_date,
    )

    try:
        show_spike_charts(chart_date)
    except Exception as exc:
        st.error("Unable to load transaction-level evidence.")
        with st.expander("Technical error"):
            st.exception(exc)


# ============================================================
# COUNTRY SALES
# ============================================================

st.divider()
st.subheader("🌍 Sales by country")

if country_df.empty:
    st.info("The country sales table returned no rows.")
else:
    country_col = find_column(
        country_df,
        ["country", "customer_country", "billing_country"],
    )

    country_revenue_col = find_column(
        country_df,
        ["total_revenue", "revenue", "total_sales", "sales"],
    )

    if country_col is None or country_revenue_col is None:
        show_missing_column_message(COUNTRY_TABLE, country_df)
    else:
        country_view = country_df.copy()
        country_view[country_revenue_col] = pd.to_numeric(
            country_view[country_revenue_col],
            errors="coerce",
        )

        country_view = country_view.dropna(
            subset=[country_revenue_col]
        ).sort_values(country_revenue_col, ascending=False)

        left, right = st.columns([3, 2])

        with left:
            country_chart = country_view.head(10).set_index(country_col)

            st.bar_chart(
                country_chart[[country_revenue_col]],
                x_label="Country",
                y_label="Revenue (£)",
                horizontal=True,
                width="stretch",
            )

        with right:
            st.markdown("**Top countries**")
            st.dataframe(
                country_view.head(10),
                width="stretch",
                hide_index=True,
            )


# ============================================================
# PRODUCT PERFORMANCE
# ============================================================

st.divider()
st.subheader("📦 Product performance")

if product_df.empty:
    st.info("The product performance table returned no rows.")
else:
    product_col = find_column(
        product_df,
        [
            "description",
            "product_name",
            "stock_description",
            "stockcode",
            "product",
        ],
    )

    product_revenue_col = find_column(
        product_df,
        ["total_revenue", "revenue", "total_sales", "sales"],
    )

    if product_col is None or product_revenue_col is None:
        show_missing_column_message(PRODUCT_TABLE, product_df)
    else:
        product_view = product_df.copy()
        product_view[product_revenue_col] = pd.to_numeric(
            product_view[product_revenue_col],
            errors="coerce",
        )

        product_view = product_view.dropna(
            subset=[product_revenue_col]
        ).sort_values(product_revenue_col, ascending=False)

        left, right = st.columns([3, 2])

        with left:
            top_products = product_view.head(10).copy()
            top_products[product_col] = (
                top_products[product_col].astype(str).str.slice(0, 55)
            )
            top_products = top_products.set_index(product_col)

            st.bar_chart(
                top_products[[product_revenue_col]],
                x_label="Product",
                y_label="Revenue (£)",
                horizontal=True,
                width="stretch",
            )

        with right:
            st.markdown("**Top products by revenue**")
            st.dataframe(
                product_view.head(10),
                width="stretch",
                hide_index=True,
            )


# ============================================================
# AI AGENT CHAT
# ============================================================

st.divider()
st.subheader("🤖 Ask the Retail Operations AI Agent")

st.write(
    "Ask questions about revenue, countries, products, customers, "
    "invoices, data quality, or unusual sales."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if message.get("evidence"):
            with st.expander("Databricks evidence used"):
                st.json(message["evidence"])

question = st.chat_input(
    "Example: Investigate the revenue spike on 2011-12-09"
)

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("The AI agent is querying Databricks..."):
            try:
                result = ask_agent(question)

                if isinstance(result, dict):
                    answer = result.get(
                        "answer",
                        "The agent did not return an answer.",
                    )
                    evidence = result.get("evidence", [])
                else:
                    answer = str(result)
                    evidence = []

                st.markdown(answer)

                with st.expander("Databricks evidence used"):
                    if evidence:
                        st.json(evidence)
                    else:
                        st.info("No tool evidence was returned.")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "evidence": evidence,
                    }
                )

            except Exception as exc:
                st.error("The AI agent could not complete the request.")
                st.exception(exc)


# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "Retail Operations AI · Databricks SQL + Python + Streamlit "
    "+ AI tool calling"
)
