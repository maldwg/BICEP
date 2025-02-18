import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Data for the heatmap
ids = ["IDS-A", "IDS-B", "IDS-C", "IDS-D", "IDS-E"]
metrics = ["FPR", "FNR", "DR", "FDR", "Accuracy", "Precision", "F1-score", "Unassigned Ratio"]
data = np.array([
    [0.05, 0.10, 0.90, 0.08, 0.92, 0.91, 0.905, 0.02],
    [0.07, 0.12, 0.88, 0.10, 0.90, 0.89, 0.885, 0.03],
    [0.04, 0.08, 0.92, 0.07, 0.93, 0.92, 0.915, 0.01],
    [0.06, 0.09, 0.91, 0.09, 0.91, 0.90, 0.905, 0.02],
    [0.05, 0.07, 0.93, 0.06, 0.94, 0.93, 0.925, 0.01]
])

# Create the heatmap
plt.figure(figsize=(10, 6))
sns.heatmap(data, annot=True, cmap="Blues", xticklabels=metrics, yticklabels=ids, fmt=".3f")

# Labels and title
plt.xlabel("Metrics")
plt.xticks(rotation=45, ha="right")
plt.ylabel("IDS")
plt.yticks(rotation=0, ha="right")

plt.title("Heatmap of IDS Performance Metrics")
plt.tight_layout()
plt.savefig("./heatmap.svg", format='svg')
