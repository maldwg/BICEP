import matplotlib.pyplot as plt
import numpy as np

# Average runtimes for partial dataset (seconds)
runtimes_partial = {
    "suricata": 9.13,
    "suricata_ensemble": 9.62,
    "snort": 5.96,
    "snort_ensemble": 9.05,
    "slips": 6672.29,
    "slips_ensemble": 6778.00,
}

# Average runtimes for full dataset (seconds)
runtimes_full = {
    "suricata": 2537.96,
    "suricata_ensemble": 9639.45,
    "snort": 1558.72,
    "snort_ensemble": 3197.64,
}

# Plot runtimes (log scale helps since SLIPS is much slower)
def plot_runtimes(data, title):
    names = list(data.keys())
    values = list(data.values())

    plt.figure(figsize=(8, 5))
    bars = plt.bar(names, values, color="skyblue", edgecolor="black")
    plt.yscale("log")
    plt.ylabel("Runtime (s, log scale)")
    plt.title(title)

    # annotate bars
    for bar, val in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width()/2, val, f"{val:.1f}",
                 ha='center', va='bottom', fontsize=8)
    plt.show()

plot_runtimes(runtimes_partial, "Average Runtimes (Partial Dataset)")
plot_runtimes(runtimes_full, "Average Runtimes (Full Dataset)")
