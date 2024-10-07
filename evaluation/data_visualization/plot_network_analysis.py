import matplotlib.pyplot as plt
import numpy as np

# Example dataset with counts for each class
def create_bar_plot(data, title, path):
    # Labels and values
    labels = list(data.keys())
    values = list(data.values())

    # Create the bar chart
    fig, ax = plt.subplots()
    ax.bar(labels, values, color=['#4CAF50', '#FF6347'])  # Green for benign, red for malicious

    # Add labels and title
    ax.set_xlabel('IDS')
    ax.set_ylabel('Amount of alerts')
    ax.set_title(title)

    # Save as SVG
    plt.savefig(path, format='svg')

data = {'Suricata': 450, 'Slips': 150}
title = "Suricata vs. Slips using tmNIDS"
path = "/mnt/c/Users/Max/Desktop/suricata-vs-slips-tmNIDS.svg"
create_bar_plot(data, title, path)