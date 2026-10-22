# Retail Operations Agentic AI

An end-to-end retail analytics project integrating **Databricks, Python, SQL, data quality validation, interactive dashboards, and a conversational AI chatbot** to transform retail transaction data into actionable business insights.

**GitHub Repository:** [retail-ops-agent](https://github.com/SraddhanjaliBarik/retail-ops-agent)

## Project Overview

This project demonstrates an end-to-end retail analytics workflow using the UCI Online Retail dataset. It combines data ingestion, data cleaning, analytical transformations, business KPI reporting, and AI-assisted transaction investigation.

The solution brings together a Databricks data pipeline, a retail analytics dashboard, and a conversational chatbot powered by a Python AI agent and data tools. Users can explore retail performance, investigate unusual transactions, and ask business questions using natural language.

## Solution Architecture

```text
             UCI Online Retail Dataset
                       |
                       v
              Databricks Platform
                       |
             +---------+---------+
             |         |         |
             v         v         v
          Bronze     Silver     Gold
          Ingestion  Cleaning   Analytics
             |         |         |
             +---------+---------+
                       |
                 Curated Data
                       |
             +---------+---------+
             |                   |
             v                   v
      Retail Dashboard    Conversational Chatbot
      KPIs and Trends             |
                                  v
                           Python AI Agent
                                  |
                                  v
                         SQL and Data Tools
                                  |
                                  v
                         Retail Data Insights
```

## Key Features

### 1. Databricks Data Engineering

- Ingest retail transaction data into the Bronze layer.
- Clean and validate records in the Silver layer.
- Prepare analytical datasets and business metrics in the Gold layer.
- Use SQL to transform, query, and analyze retail data.

### 2. Data Quality and Transaction Analysis

- Identify missing, invalid, or inconsistent data.
- Validate transaction records and relevant fields.
- Investigate unusual invoice quantities and transaction patterns.
- Compare individual invoices with the broader dataset using statistical analysis.

### 3. Retail Analytics Dashboard

The dashboard provides a visual overview of retail performance, supporting analysis of:

- Key performance indicators (KPIs).
- Daily sales trends.
- Product-level performance.
- Country-level sales.
- Transaction quantities and unusual patterns.

### 4. Conversational AI Chatbot

The chatbot provides a natural-language interface for exploring retail data and investigating business questions.

Users can ask questions without manually writing SQL. The chatbot works with the Python AI agent and its available data tools to retrieve or analyze relevant information.

**Example business questions:**

- How do sales change over time?
- Which products generate the highest revenue?
- Which countries contribute most to sales?
- Investigate invoice 581483 and compare its quantity with other invoices.
- Which transactions contain unusual quantities that warrant further investigation?

### 5. Python AI Agent and Data Tools

The Python AI agent acts as the reasoning and tool-execution layer behind the chatbot.

- Interprets business questions.
- Selects appropriate data tools for supported requests.
- Retrieves or analyzes relevant retail information.
- Explains analytical results in business-friendly language.

Statistical outliers are treated as indicators for further investigation, not as proof of fraud or incorrect transactions.

## Technology Stack

| Category | Technologies |
|---|---|
| Data platform | Databricks |
| Data processing | Python, SQL |
| Data engineering | Bronze, Silver, Gold architecture |
| Data source | UCI Online Retail dataset |
| AI application | Python AI agent, conversational chatbot, data tools |
| Business intelligence | Retail analytics dashboard, KPIs, trend analysis |
| Version control | Git, GitHub |

## Dataset

This project uses the **Online Retail** dataset from the UCI Machine Learning Repository.

The dataset contains retail transaction information, including invoice identifiers, product descriptions, quantities, invoice dates, unit prices, customer identifiers, and countries.

**Source:** [UCI Machine Learning Repository — Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail)

The raw dataset is excluded from the GitHub repository to avoid committing large data files.

## Databricks Notebooks

The data preparation and analytics workflow includes the following notebooks:

1. `01_bronze_ingestion` — ingests the source retail data.
2. `02_silver_cleaning` — cleans and validates transaction records.
3. `03_gold_analytics` — prepares analytical outputs and business metrics.

## Project Structure

```text
retail-ops-agent/
├── src/
│   ├── agent.py
│   └── retail_tools.py
├── app.py
├── convert_data.py
├── test_invoice_comparison.py
├── test_outliers.py
├── test_validation.py
├── .gitignore
└── README.md
```

The repository may contain additional supporting files. Local datasets, credentials, virtual environments, and generated exports should remain excluded from version control.

## Getting Started

### Prerequisites

- Python 3.12 or a compatible version.
- Git.
- A Databricks workspace with access to the required data and SQL resources.
- The Python dependencies required by the application.
- Securely configured Databricks connection credentials.

### 1. Clone the repository

```bash
git clone https://github.com/SraddhanjaliBarik/retail-ops-agent.git
cd retail-ops-agent
```

### 2. Create a virtual environment

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

If a `requirements.txt` file is available:

```bash
pip install -r requirements.txt
```

Otherwise, install the packages required by the project as documented in its source code.

### 4. Configure Databricks connectivity

Configure the connection settings required by the application using environment variables or a local `.env` file, according to the implementation.

**Security:** Never commit access tokens, passwords, or other secrets to GitHub. Keep `.env` excluded through `.gitignore`.

### 5. Run the dashboard

If `app.py` is the Streamlit application entry point and all required dependencies are installed:

```bash
streamlit run app.py
```

Run the data-processing notebooks in Databricks to execute the ingestion, cleaning, and analytics workflow.

## Testing

The repository includes test files covering invoice quantity comparison, outlier analysis, and data validation.

Run the tests after installing the required dependencies:

```bash
python -m pytest
```

## Responsible AI and Data Analysis

- Validate source data before interpreting analytical results.
- Treat unusual statistical patterns as investigation signals rather than definitive conclusions.
- Avoid exposing credentials or sensitive data through chatbot responses, logs, or source control.
- Verify business context before making operational decisions based on AI-generated explanations.

## Future Enhancements

- Complete and document the integration between Databricks notebooks and GitHub.
- Expand automated data quality checks and test coverage.
- Improve chatbot evaluation and tool reliability.
- Add dashboard screenshots and a project demonstration.
- Document reproducible deployment and configuration procedures.

## Author

**Sraddhanjali Barik**

GitHub: [SraddhanjaliBarik](https://github.com/SraddhanjaliBarik)

---

*This portfolio project demonstrates practical skills in retail analytics, data engineering, data quality, business intelligence, and AI-assisted data exploration.*

