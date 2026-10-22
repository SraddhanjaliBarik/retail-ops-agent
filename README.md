
# Retail Operations Agentic AI

An end-to-end retail analytics portfolio project combining **Databricks, SQL, Python, data quality validation, dashboards, and an AI agent** to explore retail transactions and investigate unusual business patterns.

**GitHub Repository:** [retail-ops-agent](https://github.com/SraddhanjaliBarik/retail-ops-agent)

## Project Overview

This project uses the UCI Online Retail dataset to build a retail analytics workflow in Databricks. It covers data ingestion, cleaning, analytical transformations, business KPI reporting, and AI-assisted investigation of retail transactions.

The goal is to demonstrate how data engineering, analytics, and AI can work together to support data-driven retail operations.

## Architecture

```text
UCI Online Retail Dataset
          |
          v
Databricks Bronze Layer
Raw data ingestion
          |
          v
Databricks Silver Layer
Data cleaning and validation
          |
          v
Databricks Gold Layer
Business aggregations and KPIs
          |
          +--------------------+
          |                    |
          v                    v
Retail Dashboard         Python AI Agent
                         |
                         v
                    SQL / Data Tools
                         |
                         v
                 Evidence-based answers
```

## Key Features

### 1. Data Engineering with Databricks

- Ingest retail transaction data into the Bronze layer.
- Clean and validate records in the Silver layer.
- Prepare business-oriented analytics in the Gold layer.
- Use SQL to explore transaction data and calculate retail metrics.

### 2. Data Quality and Validation

- Handle missing and invalid values.
- Clean transaction dates and relevant fields.
- Support data validation and anomaly investigation.
- Compare unusual transaction quantities with the broader dataset.

### 3. Retail Analytics Dashboard

The dashboard is designed to help explore retail business performance through:

- Key performance indicators (KPIs).
- Daily sales trends.
- Product-level analysis.
- Country-level analysis.
- Transaction and quantity patterns.

### 4. Python AI Agent

The project includes a Python-based agent that can use data tools to investigate retail questions.

Example question:

> Investigate invoice 581483 and compare its quantity with all invoices. Explain the statistical result without assuming fraud.

The analysis can compare an invoice's quantity with the overall distribution and explain statistical outliers. An unusual result is an investigation signal, not proof of fraud.

## Technology Stack

| Area | Technologies |
|---|---|
| Cloud analytics | Databricks |
| Data processing | Python, SQL |
| Data engineering | Bronze, Silver, Gold layers |
| Data source | UCI Online Retail dataset |
| AI application | Python-based agent and data tools |
| Analytics | KPIs, transaction analysis, dashboards |
| Version control | Git and GitHub |

## Dataset

The project uses the **Online Retail** dataset from the UCI Machine Learning Repository.

The dataset contains retail transaction records, including invoice identifiers, products, quantities, invoice dates, prices, customer identifiers, and countries.

Dataset source: [UCI Machine Learning Repository — Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail)

The original dataset is not committed to this repository. Download it separately and follow the project setup instructions.

## Databricks Notebooks

The workspace contains the following notebooks:

1. `01_bronze_ingestion` — initial data ingestion.
2. `02_silver_cleaning` — data cleaning and validation.
3. `03_gold_analytics` — analytical transformations and business metrics.

Notebook files should be included in the GitHub repository when ready to share.

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

Additional files may be present in the repository. Keep local datasets, environment files, and credentials out of version control.

## Getting Started

### Prerequisites

- Python 3.12 or a compatible Python version.
- Git.
- A Databricks workspace with access to the required compute and SQL resources.
- Databricks connection credentials configured securely.
- The required Python packages for the application.

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

Install the packages required by the application. If a `requirements.txt` file is added to the repository, use:

```bash
pip install -r requirements.txt
```

### 4. Configure Databricks access

Configure the connection values required by the application using environment variables or a local `.env` file, according to the code's configuration.

**Never commit access tokens, passwords, or other secrets to GitHub.** Keep `.env` excluded through `.gitignore`.

### 5. Run the application

If `app.py` is the Streamlit dashboard entry point and its dependencies are installed, start it with:

```bash
streamlit run app.py
```

Run the notebooks in Databricks for the data ingestion and transformation workflow.

## Example Business Questions

- How do sales change over time?
- Which products contribute most to sales?
- Which countries generate the highest revenue?
- Which invoices contain unusual quantities?
- How does a selected invoice compare with the overall transaction distribution?
- What data quality issues should be investigated?

## Testing

The repository includes test files for invoice quantity comparison, outlier analysis, and data validation.

Run the relevant tests after installing the required dependencies:

```bash
python -m pytest
```

## Security and Responsible Analysis

- Do not commit credentials, tokens, or private configuration.
- Keep raw datasets and generated exports out of version control unless explicitly intended.
- Treat statistical outliers as signals for investigation, not proof of fraud or incorrect transactions.
- Verify data quality and business context before acting on analytical findings.

## Future Improvements

- Complete the integration of the Databricks notebooks with the GitHub repository.
- Improve automated data quality checks.
- Expand AI-agent tools and evaluation tests.
- Add dashboard screenshots and a demonstration.
- Document reproducible setup and deployment steps.

## Author

Sraddhanjali Barik

GitHub: [SraddhanjaliBarik](https://github.com/SraddhanjaliBarik)

---

*This project is a portfolio demonstration of retail data analytics, data engineering, and AI-assisted investigation.*
