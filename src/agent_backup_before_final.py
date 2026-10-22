
import json
import os
import re

from dotenv import load_dotenv
from databricks_openai import DatabricksOpenAI

from src.retail_tools import (
    get_daily_sales,
    get_top_products,
    get_country_sales,
    get_customer_purchase_history,
    get_product_sales_history,
    get_invoice_details,
    validate_invoice,
    investigate_revenue_spike,
)

load_dotenv()

MODEL = os.getenv(
    "DATABRICKS_MODEL",
    "databricks-meta-llama-3-3-70b-instruct",
)

client = DatabricksOpenAI()


def json_safe(data):
    return json.dumps(data, default=str, ensure_ascii=False)


# Each tool has a defined schema so the model can request
# structured arguments rather than relying on keyword routing.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_daily_sales",
            "description": "Retrieve recent daily sales KPI records.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of recent daily records, 1 to 90.",
                    }
                },
                "required": ["days"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_country_sales",
            "description": "Retrieve countries ranked by revenue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer"},
                },
                "required": ["limit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_products",
            "description": "Retrieve products ranked by revenue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer"},
                },
                "required": ["limit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_invoice",
            "description": "Check invoice totals, quantities, and price anomalies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_no": {"type": "string"},
                },
                "required": ["invoice_no"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_invoice_details",
            "description": "Retrieve line items for a specific invoice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_no": {"type": "string"},
                },
                "required": ["invoice_no"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_purchase_history",
            "description": "Retrieve recent purchase history for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": ["customer_id", "limit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_sales_history",
            "description": "Retrieve recent sales history for a stock code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stock_code": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["stock_code", "limit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "investigate_revenue_spike",
            "description": "Retrieve transaction lines for investigating a date's revenue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sales_date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format.",
                    },
                },
                "required": ["sales_date"],
                "additionalProperties": False,
            },
        },
    },
]


def run_tool(name, args):
    """Execute only explicitly allowlisted, read-only Python tools."""

    if name == "get_daily_sales":
        days = int(args["days"])
        if not 1 <= days <= 90:
            raise ValueError("days must be between 1 and 90")
        return get_daily_sales(days)

    if name == "get_country_sales":
        limit = int(args["limit"])
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        return get_country_sales(limit)

    if name == "get_top_products":
        limit = int(args["limit"])
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        return get_top_products(limit)

    if name == "validate_invoice":
        invoice_no = str(args["invoice_no"])
        if not re.fullmatch(r"\d{1,20}", invoice_no):
            raise ValueError("Invalid invoice number")
        return validate_invoice(invoice_no)

    if name == "get_invoice_details":
        invoice_no = str(args["invoice_no"])
        if not re.fullmatch(r"\d{1,20}", invoice_no):
            raise ValueError("Invalid invoice number")
        return get_invoice_details(invoice_no)

    if name == "get_customer_purchase_history":
        customer_id = int(args["customer_id"])
        limit = int(args["limit"])
        if customer_id <= 0 or not 1 <= limit <= 100:
            raise ValueError("Invalid customer ID or limit")
        return get_customer_purchase_history(customer_id, limit)

    if name == "get_product_sales_history":
        stock_code = str(args["stock_code"])
        limit = int(args["limit"])
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,50}", stock_code):
            raise ValueError("Invalid stock code")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        return get_product_sales_history(stock_code, limit)

    if name == "investigate_revenue_spike":
        sales_date = str(args["sales_date"])
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sales_date):
            raise ValueError("Date must use YYYY-MM-DD")
        return investigate_revenue_spike(sales_date)

    raise ValueError(f"Tool is not allowed: {name}")


def ask_agent(question, max_tool_rounds=5):
    """Let the model select tools and reason over their returned evidence."""

    messages = [
        {
            "role": "system",
            "content": (
                "You are a retail operations data analyst. "
                "Use tools to retrieve evidence before answering data questions. "
                "You may call multiple tools when needed. "
                "Revenue is in GBP; format it as £ with two decimals. "
                "Do not invent data or causes. Distinguish facts from hypotheses. "
                "A statistical outlier is not proof of fraud or a data error. "
                "Explain when evidence is insufficient."
            ),
        },
        {"role": "user", "content": question},
    ]

    evidence = []

    for _ in range(max_tool_rounds):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=1200,
        )

        message = response.choices[0].message
        tool_calls = message.tool_calls

        if not tool_calls:
            return {
                "answer": message.content or "The model returned no text.",
                "evidence": evidence,
            }

        messages.append(message.model_dump(exclude_none=True))

        for call in tool_calls:
            name = call.function.name

            try:
                args = json.loads(call.function.arguments or "{}")
                result = run_tool(name, args)
                evidence.append({
                    "tool": name,
                    "arguments": args,
                    "result": result,
                })
                tool_content = json_safe(result)
            except Exception as exc:
                tool_content = json_safe({
                    "error": str(exc),
                    "tool": name,
                })

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": tool_content,
            })

    return {
        "answer": (
            "I reached the tool-call limit before completing the answer. "
            "Please narrow the question and try again."
        ),
        "evidence": evidence,
    }


def main():
    print("Retail Operations AI Agent")
    print("Ask about sales, countries, products, invoices, customers or anomalies.")
    print("Type 'exit' to quit.\n")

    while True:
        question = input("You: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        if not question:
            continue

        try:
            result = ask_agent(question)
            print(f"\nAgent: {result['answer']}")
            print("\nEvidence retrieved:")
            print(json.dumps(result["evidence"], indent=2, default=str))
            print()
        except Exception as exc:
            print(f"\nAgent error: {exc}\n")


if __name__ == "__main__":
    main()
