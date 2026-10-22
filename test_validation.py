
from src.retail_tools import (
    get_customer_purchase_history,
    get_product_sales_history,
    get_invoice_details,
    validate_invoice,
)

print("\n1. CUSTOMER HISTORY")
print(get_customer_purchase_history(16446, limit=10))

print("\n2. PRODUCT HISTORY")
print(get_product_sales_history("23843", limit=10))

print("\n3. INVOICE DETAILS")
print(get_invoice_details("581483"))

print("\n4. INVOICE VALIDATION")
print(validate_invoice("581483"))
