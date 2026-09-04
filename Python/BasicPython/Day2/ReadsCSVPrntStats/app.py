import pandas as pd

# Read the CSV
df = pd.read_csv("data.csv")

# Print basic summary stats
print("ROWS:", len(df))
print("COLUMNS:", list(df.columns))
print("\nSUMMARY STATS:")
print(df.describe())