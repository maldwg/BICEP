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
    bars_total = ax.bar(labels, total_values, label='Total Alerts', color='blue')
    # for i, bar in enumerate(bars_total):
    #     ax.bar(bar.get_x() + bar.get_width() / 2, assignable_values[i],
    #            width=bar.get_width(), label='Assignable Alerts', color='orange')


    ax.set_xlabel('IDS')
    ax.set_ylabel('Amount of Alerts')
    ax.set_title(title)

    handles, labels = ax.get_legend_handles_labels()
    unique_labels = dict(zip(labels, handles))  # Remove duplicates
    # ax.legend(unique_labels.values(), unique_labels.keys())

    plt.tight_layout()
    plt.savefig(path, format='svg')

# Sample data
data = {
    'Suricata': {"total": 5397, "assignable": 2051},
    'Slips': {"total": 73, "assignable": 37},
    'Ensemble': {"total": 67, "assignable": 67}
}

title = "Suricata vs. Slips using BUP"
path = "/mnt/c/Users/Max/Desktop/suricata-vs-slips-bup.svg"
create_bar_plot(data, title, path)

# Suricata vs Slips on network analysis seperate (tmnids)
# core-1  | Received Logs for container Slips-36117
# core-1  | recievd 236 alerts --> 118 when considered 50 percent unassigned ratio
# core-1  | analysis-type: network
# core-1  | done
# core-1  | INFO:     172.20.0.1:42898 - "POST /ids/publish/alerts HTTP/1.1" 200 OK
# core-1  | Received Logs for container Suricata-35603
# core-1  | recievd 1070 alerts --> 407 when considered 62 percent unassigned ratio
# core-1  | analysis-type: network
# core-1  | done
# core-1  | INFO:     172.20.0.1:42914 - "POST /ids/publish/alerts HTTP/1.1" 200 OK


# Suricata vs Slips on network analysis seperate (bup)
# Suricata: 5397 --> assignable 2051 using 0,62 unassignable rate
# Slips:  --> 73 assignable 37 using 0,50 unassignable rate

# core-1  | Found 73 alerts for Slips-41215
# core-1  | There are 14879 alerts in total
# core-1  | length of total majority voted alerts is 67


# BUP single and ensemble:
# data = {
#     'Suricata': {"total": 5397, "assignable": 2051},
#     'Slips': {"total": 73, "assignable": 37},
#     'Ensemble': {"total": 5470, "assignable": 67}
# }

#tmnids single and ensemble

# data = {
#     'Suricata': {"total": 1070, "assignable": 407},
#     'Slips': {"total": 236, "assignable": 118},
#     'Ensemble': {"total": 1306, "assignable": 121}
# }
