import matplotlib.pyplot as plt
import os
import pandas as pd
from glob import glob
import numpy as np

def read_values_by_type(folder_path, type):
    """
    Function to extract the values of a file in a given path assuming a keyword in the filename.
    The CSV is expected to have 1 column as timestamp and a second one with values. No further columns.

    Args:
        folder_path (str): glob path to look at
        type (str): keyword in filename

    Returns:
        list: list with the extracted values
    """
    all_values = []
    for file in glob(os.path.join(folder_path, f"*{type}*.csv")):
        df = pd.read_csv(file)
        all_values.extend(df.iloc[:, -1].dropna().tolist())
    return all_values

# Read RAM and CPU values
suricata_ram = read_values_by_type("suricata", "Memory")
snort_ram = read_values_by_type("snort", "Memory")
suricata_reduced_ram = read_values_by_type("suricata-reduced", "Memory")
snort_reduced_ram = read_values_by_type("snort-reduced", "Memory")
slips_ram = read_values_by_type("slips", "Memory")

suricata_cpu = read_values_by_type("suricata", "CPU")
snort_cpu = read_values_by_type("snort", "CPU")
suricata_reduced_cpu = read_values_by_type("suricata-reduced", "CPU")
snort_reduced_cpu = read_values_by_type("snort-reduced", "CPU")
slips_cpu = read_values_by_type("slips", "CPU")

# Combine data
all_ram_data = [suricata_ram, snort_ram, suricata_reduced_ram, snort_reduced_ram, slips_ram]
all_cpu_data = [suricata_cpu, snort_cpu, suricata_reduced_cpu, snort_reduced_cpu, slips_cpu]
labels = ["Suricata", "Snort", "Suricata-Reduced", "Snort-Reduced", "Slips-Reduced"]

# Helper to print stats
def print_stats(data, label, unit):
    values = np.array(data)
    print(f"{label} ({unit}):")
    print(f"  Min:    {np.min(values):.2f}")
    print(f"  Max:    {np.max(values):.2f}")
    print(f"  Mean:   {np.mean(values):.2f}")
    print(f"  Median: {np.median(values):.2f}")
    print()

# Print RAM stats
print("RAM Usage Stats")
for data, label in zip(all_ram_data, labels):
    print_stats(data, label, "MB")

# Plot RAM Boxplot
fig, ax = plt.subplots(1, 1, figsize=(12, 6))
ram_box = ax.boxplot(all_ram_data, vert=True)
ax.set_title('Overall RAM Usage (MB) for All IDS Instances')
ax.set_ylabel('RAM Usage (MB)')
ax.set_xticklabels(labels)

ax.legend()
plt.tight_layout()
plt.savefig("./boxplot-ram.svg", format='svg')

# Print CPU stats
print("CPU Usage Stats")
for data, label in zip(all_cpu_data, labels):
    print_stats(data, label, "cores")

# Plot CPU Boxplot
fig, ax = plt.subplots(1, 1, figsize=(12, 6))
cpu_box = ax.boxplot(all_cpu_data, vert=True)
ax.set_title('Overall CPU Usage (cores used) for All IDS Instances')
ax.set_ylabel('CPU Usage (cores used)')
ax.set_xticklabels(labels)

ax.legend()
plt.tight_layout()
plt.savefig("./boxplot-cpu.svg", format='svg')
