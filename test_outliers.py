
from src.retail_tools import get_product_quantity_outliers

results = get_product_quantity_outliers("23843", limit=20)

for row in results:
    print(row)
