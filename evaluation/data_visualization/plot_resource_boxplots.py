import matplotlib.pyplot as plt

# Simulated data: Replace this with actual data collection
# Example data where each inner list is the resource usage (RAM/CPU) of an IDS instance over several measurements.
suricata_data = {
    'Instance_1': {'RAM_Usage_GB': [4.1, 4.3, 4.0, 4.2], 'CPU_Usage_Percent': [70, 72, 68, 71]},
    'Instance_2': {'RAM_Usage_GB': [3.9, 4.0, 3.8, 3.9], 'CPU_Usage_Percent': [65, 66, 64, 63]},
    'Instance_3': {'RAM_Usage_GB': [5.0, 5.2, 4.9, 5.1], 'CPU_Usage_Percent': [80, 78, 81, 79]},
    'Instance_4': {'RAM_Usage_GB': [4.5, 4.6, 4.7, 4.4], 'CPU_Usage_Percent': [75, 74, 77, 76]},
    'Instance_5': {'RAM_Usage_GB': [3.7, 3.6, 3.8, 3.7], 'CPU_Usage_Percent': [60, 59, 62, 61]},
    'Instance_6': {'RAM_Usage_GB': [4.2, 4.3, 4.1, 4.4], 'CPU_Usage_Percent': [85, 83, 87, 84]},
    'Instance_7': {'RAM_Usage_GB': [4.6, 4.7, 4.8, 4.5], 'CPU_Usage_Percent': [78, 80, 77, 79]}
}

snort_data = {
    'Instance_1': {'RAM_Usage_GB': [ 4.3, 4.0, 4.2], 'CPU_Usage_Percent': [72, 68, 71]},
    'Instance_2': {'RAM_Usage_GB': [ 4.0, 3.8, 3.9], 'CPU_Usage_Percent': [66, 64, 63]},
    'Instance_3': {'RAM_Usage_GB': [ 5.2, 4.9, 5.1], 'CPU_Usage_Percent': [78, 81, 79]},
    'Instance_4': {'RAM_Usage_GB': [ 4.6, 4.7, 4.4], 'CPU_Usage_Percent': [74, 77, 76]},
    'Instance_5': {'RAM_Usage_GB': [ 3.6, 3.8, 3.7], 'CPU_Usage_Percent': [59, 62, 61]},
    'Instance_6': {'RAM_Usage_GB': [ 4.3, 4.1, 4.4], 'CPU_Usage_Percent': [83, 87, 84]},
    'Instance_7': {'RAM_Usage_GB': [ 4.7, 4.8, 4.5], 'CPU_Usage_Percent': [78, 80, 77, 79]}
}

slips_data = {
    'Instance_1': {'RAM_Usage_GB': [ 4.3, 4.0], 'CPU_Usage_Percent': [72, 68, 71]},
    'Instance_2': {'RAM_Usage_GB': [ 4.0, 3.8], 'CPU_Usage_Percent': [66, 64, 63]},
    'Instance_3': {'RAM_Usage_GB': [ 5.2, 4.9, 5.1], 'CPU_Usage_Percent': [78, 81, 79]},
    'Instance_4': {'RAM_Usage_GB': [ 4.6, 4.7, 4.4], 'CPU_Usage_Percent': [74, 77, 76]},
    'Instance_5': {'RAM_Usage_GB': [ 3.6, 3.8, 3.7], 'CPU_Usage_Percent': [59, 62, 61]},
    'Instance_6': {'RAM_Usage_GB': [ 4.3, 4.1, 4.4], 'CPU_Usage_Percent': [83, 87, 84]},
    'Instance_7': {'RAM_Usage_GB': [ 4.7, 4.8, 4.5], 'CPU_Usage_Percent': [78, 80, 77, 79]}
}


# Aggregating all data points for RAM and CPU across all instances
suricata_ram_data = [value for instance in suricata_data.values() for value in instance['RAM_Usage_GB']]
suricata_cpu_data = [value for instance in suricata_data.values() for value in instance['CPU_Usage_Percent']]

snort_ram_data = [value for instance in snort_data.values() for value in instance['RAM_Usage_GB']]
snort_cpu_data = [value for instance in snort_data.values() for value in instance['CPU_Usage_Percent']]


slips_ram_data = [value for instance in slips_data.values() for value in instance['RAM_Usage_GB']]
slips_cpu_data = [value for instance in slips_data.values() for value in instance['CPU_Usage_Percent']]

all_ram_data = [suricata_ram_data, snort_ram_data, slips_ram_data]
all_cpu_data = [suricata_cpu_data, snort_cpu_data, slips_cpu_data]

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
