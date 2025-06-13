import matplotlib.pyplot as plt
import os
import pandas as pd
from glob import glob

def read_values_by_type(folder_path, type):
    """
    Function to extract the values of a file in a given path assuiming a keyword in the filename
    The csv is to be expected to have 1 col as timestamp and a second one with values. No further columns.

    Args:
        folder_path (str): glob path to look at
        type (str): keyword in filename

    Returns:
        list: list with the extracted values
    """
    all_values = []
    for file in glob(os.path.join(folder_path, f"*{type}*.csv")):
        df = pd.read_csv(file)
        # read only the last column as values
        all_values.extend(df.iloc[:, -1].dropna().tolist())
    return all_values

suricata_ram = read_values_by_type("suricata", "Memory")
snort_ram = read_values_by_type("snort", "Memory")
suricata_reduced_ram = read_values_by_type("suricata-reduced", "Memory")
snort_reduced_ram = read_values_by_type("snort-reduced", "Memory")
slips_ram = read_values_by_type("slips-reduced", "Memory")

suricata_cpu = read_values_by_type("suricata", "CPU")
snort_cpu = read_values_by_type("snort", "CPU")
suricata_reduced_cpu = read_values_by_type("suricata-reduced", "CPU")
snort_reduced_cpu = read_values_by_type("snort-reduced", "CPU")
slips_cpu = read_values_by_type("slips-reduced", "CPU")

all_ram_data = [suricata_ram, snort_ram, suricata_reduced_ram, snort_reduced_ram, slips_ram]
all_cpu_data = [suricata_cpu, snort_cpu, suricata_reduced_cpu, snort_reduced_cpu, slips_cpu]


# Plotting boxplots for aggregated data
fig, ax = plt.subplots(1,1,figsize=(12, 6))

# Boxplot for overall RAM usage across all instances
ax.boxplot(all_ram_data, vert=True)
ax.set_title('Overall RAM Usage (GB) for All IDS Instances')
ax.set_ylabel('RAM Usage (GB)')
ax.set_xticklabels(["Suricata", "Snort", "Slips"])


plt.tight_layout()
plt.savefig("./boxplot-ram.svg", format='svg')

fig, ax = plt.subplots(1,1,figsize=(12, 6))
# Boxplot for overall CPU usage across all instances
ax.boxplot(all_cpu_data, vert=True)
ax.set_title('Overall CPU Usage (%) for All IDS Instances')
ax.set_ylabel('CPU Usage (%)')
ax.set_xticklabels(["Suricata", "Snort", "Slips"])
plt.tight_layout()
plt.savefig("./boxplot-cpu.svg", format='svg')
