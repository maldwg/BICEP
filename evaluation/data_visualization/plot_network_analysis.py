import matplotlib.pyplot as plt
import numpy as np

# Example dataset with counts for each class
import matplotlib.pyplot as plt

def create_bar_plot(data, title, path):
    # Labels and values
    labels = list(data.keys())
    total_values = [v["total"] for v in data.values()]
    assignable_values = [v["assignable"] for v in data.values()]

    fig, ax = plt.subplots()
    bars_total = ax.bar(labels, total_values, label='Total Alerts', color='skyblue')
    for i, bar in enumerate(bars_total):
        ax.bar(bar.get_x() + bar.get_width() / 2, assignable_values[i],
               width=bar.get_width(), label='Assignable Alerts', color='orange')


    ax.set_xlabel('IDS')
    ax.set_ylabel('Amount of Alerts')
    ax.set_title(title)

    handles, labels = ax.get_legend_handles_labels()
    unique_labels = dict(zip(labels, handles))  # Remove duplicates
    ax.legend(unique_labels.values(), unique_labels.keys())

    plt.tight_layout()
    plt.savefig(path, format='svg')

# Sample data
data = {
    'Suricata': {"total": 1070, "assignable": 407},
    'Slips': {"total": 228, "assignable": 109}
}

title = "Suricata vs. Slips using tmNIDS"
path = "/mnt/c/Users/Max/Desktop/suricata-vs-slips-tmNIDS.svg"
create_bar_plot(data, title, path)

# Suricata vs Slips on network analysis seperate (tmnids)
# core-1  | Received Logs for container Slips-36117
# core-1  | recievd 228 alerts --> 109 when considered 52 percent unassigned ratio
# core-1  | analysis-type: network
# core-1  | done
# core-1  | INFO:     172.20.0.1:42898 - "POST /ids/publish/alerts HTTP/1.1" 200 OK
# core-1  | Received Logs for container Suricata-35603
# core-1  | recievd 1070 alerts --> 407 when considered 52 percent unassigned ratio
# core-1  | analysis-type: network
# core-1  | done
# core-1  | INFO:     172.20.0.1:42914 - "POST /ids/publish/alerts HTTP/1.1" 200 OK


# Suricata vs Slips on network analysis seperate (tmnids)
