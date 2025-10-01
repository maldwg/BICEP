import pandas as pd
import ast

df = pd.read_csv("./benchmarking_results/ids_results_partial_datasets.csv")

# Convert Metrics column (string dict) into actual dicts
df["Metrics"] = df["Metrics"].apply(ast.literal_eval)

# Expand metrics into separate columns
metrics_df = df["Metrics"].apply(pd.Series)
df = pd.concat([df.drop(columns=["Metrics"]), metrics_df], axis=1)

median_runtimes = df.groupby("Dataset")["Runtime"].median()

avg_metrics_by_dataset = df.groupby("Dataset").mean(numeric_only=True)

# --- Print summaries ---
print("=== Median Runtime per Dataset ===")
print(median_runtimes, "\n")

print("=== Average Metrics by Dataset ===")
print(avg_metrics_by_dataset, "\n")