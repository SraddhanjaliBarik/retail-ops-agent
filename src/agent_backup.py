
import os

from dotenv import load_dotenv
from databricks_openai import DatabricksOpenAI

from src.retail_tools import (
    get_daily_sales,
    get_top_products,
    get_country_sales,
)

load_dotenv()

MODEL = os.getenv(
    "DATABRICKS_MODEL",
    "databricks-meta-llama-3-3-70b-instruct",
)


def select_data(question: str) -> tuple[list[dict], str]:
    """Choose the relevant Databricks tool based on the question."""

    q = question.lower()

    country_keywords = [
        "country",
        "countries",
        "market",
        "markets",
        "nation",
        "nations",
        "germany",
        "france",
        "netherlands",
        "ire",
        "eire",
        "united kingdom",
        "uk",
    ]

    product_keywords = [
        "product",
        "products",
        "item",
        "items",
        "stockcode",
        "top-selling",
        "top selling",
        "best-selling",
        "best selling",
    ]

    if any(word in q for word in country_keywords):
        rows = get_country_sales(10)
        label = "Top 10 countries ranked by total revenue"

    elif any(word in q for word in product_keywords):
        rows = get_top_products(10)
        label = "Top 10 products ranked by total revenue"

    else:
        rows = get_daily_sales(7)
        label = "Latest 7 available daily sales records"

    return rows, label


def main():
    client = DatabricksOpenAI()

    print("Retail Sales AI Agent")
    print("Ask about daily sales, countries, or products.")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("You: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        if not question:
            continue

        try:
            rows, data_label = select_data(question)

            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a retail data analyst. Answer using only "
                            "the supplied Databricks data. Do not invent figures. "
                            "All revenue values in this dataset are in British pounds "
                            "(GBP). Always format revenue as £ with two decimal places. "
                            "Never convert revenue to dollars or euros. If the data does "
                            "not answer the question, " 
                            "clearly explain the limitation. For country questions, "
                            "the supplied rows are countries ranked by revenue. "
                            "For product questions, the supplied rows are products "
                            "ranked by revenue. For daily sales questions, the "
                            "supplied rows are recent available daily records. "
                            "Do not claim that the data contains records it does "
                            "not contain."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {question}\n\n"
                            f"Dataset: {data_label}\n"
                            f"Data:\n{rows}"
                        ),
                    },
                ],
                max_tokens=500,
            )

            answer = response.choices[0].message.content
            print(f"\nAgent: {answer}\n")

        except Exception as exc:
            print(f"\nError: {exc}\n")


if __name__ == "__main__":
    main()
