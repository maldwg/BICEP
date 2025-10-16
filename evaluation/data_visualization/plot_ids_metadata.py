import pandas as pd
import ast

filename = "ids_results_full_datasets"
df = pd.read_csv(f"./benchmarking_results/{filename}.csv")

# Convert Metrics column (string dict) into actual dicts
df["Metrics"] = df["Metrics"].apply(ast.literal_eval)

# Expand metrics into separate columns
metrics_df = df["Metrics"].apply(pd.Series)
df = pd.concat([df.drop(columns=["Metrics"]), metrics_df], axis=1)


def classify_ids(name: str) -> str:
    # check if ensemble (has "+")
    if "+" in name:
        parts = name.split("+")
        parts = [p.strip() for p in parts]
        
        has_snort = any("snort" in p.lower() for p in parts)
        has_suricata = any("suricata" in p.lower() for p in parts)
        has_slips = any("slips" in p.lower() for p in parts)
  
        if has_suricata and has_slips and has_snort:
            return "Suricata + Slips + Snort Ensemble"       
        if has_snort and has_suricata:
            return "Snort + Suricata Ensemble"
        if has_snort and has_slips:
            return "Snort + Slips Ensemble"
        if has_suricata and has_slips:
            return "Suricata + Slips Ensemble"
        elif has_snort:
            return "Snort Ensemble"
        elif has_suricata:
            return "Suricata Ensemble"
        elif has_slips:
            return "Slips Ensemble"
        else:
            return "Other Ensemble"
    else:
        if "snort" in name.lower():
            return "Snort"
        elif "suricata" in name.lower():
            return "Suricata"
        elif "slips" in name.lower():
            return "Slips"
        else:
            return "Other"

df["IDS_Group"] = df["IDS"].map(classify_ids)


median_runtimes = df.groupby("IDS")["Runtime"].median()
avg_metrics_by_dataset = df.groupby("IDS").mean(numeric_only=True)

# --- Print summaries ---
print("=== Median Runtime per IDS config ===")
print(median_runtimes, "\n")

print("=== Average Metrics by IDS config ===")
print(avg_metrics_by_dataset, "\n")


median_runtimes = df.groupby("IDS_Group")["Runtime"].median()
avg_metrics_by_dataset = df.groupby("IDS_Group").mean(numeric_only=True)

# --- Print summaries ---
print("=== Median Runtime per IDS ===")
print(median_runtimes, "\n")

print("=== Average Metrics by IDS ===")
print(avg_metrics_by_dataset, "\n")



import numpy as np
import matplotlib.pyplot as plt

# pick the metrics you want
metrics = ["PRECISION", "FDR", "FNR", "DR", "FPR", "ACCURACY"]
N = len(metrics)

## angles for the radar chart
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]  # close the circle

# split ensembles vs non-ensembles
ensembles = avg_metrics_by_dataset[avg_metrics_by_dataset.index.str.contains("ensemble", case=False)]
non_ensembles = avg_metrics_by_dataset[~avg_metrics_by_dataset.index.str.contains("ensemble", case=False)]

# create a figure with two polar subplots stacked vertically
fig, axes = plt.subplots(
    nrows=1, ncols=2, figsize=(12, 8), 
    subplot_kw=dict(polar=True), 
)
def plot_radar(ax, data, title):
    for idx, row in data.iterrows():
        label = idx
        label = label.replace("Ensemble", "").strip()
        values = row[metrics].tolist()
        values += values[:1]
        ax.plot(angles, values, label=label)
        ax.fill(angles, values, alpha=0.25)
    ax.set_rgrids([0.2, 0.4, 0.6, 0.8])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics)
    for label in ax.get_xticklabels():
        # move label outward
        label.set_y(label.get_position()[1] - 0.1)  
    ax.set_title(title, size=16, pad=30)
    ax.legend(loc="upper center", bbox_to_anchor=(0.6, -0.1), frameon=False)

# plot
if not non_ensembles.empty:
    plot_radar(axes[0], non_ensembles, "IDS Groups (Single Systems)")
if not ensembles.empty:
    plot_radar(axes[1], ensembles, "IDS Ensembles")
    
plt.tight_layout()
fig.subplots_adjust(wspace=0.5)
plt.show()
plt.savefig(f"./ids-metadata-{filename}.svg", format="svg")

