
from src.retail_tools import compare_invoice_quantity_with_all

results = compare_invoice_quantity_with_all("581483")

for row in results:
    print(row)
