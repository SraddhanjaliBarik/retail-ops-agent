
from pathlib import Path
import pandas as pd

source = Path("data/Online Retail.xlsx")
output = Path("data/online_retail.csv")

df = pd.read_excel(source, engine="openpyxl")

print("Original rows:", len(df))
print("Columns:", df.columns.tolist())

df.to_csv(output, index=False)

print("CSV created:", output.resolve())
print("Output rows:", len(df))
print(df.head())
