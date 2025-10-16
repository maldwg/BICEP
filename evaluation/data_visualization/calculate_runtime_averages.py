import csv
import sys
from statistics import mean
import matplotlib.pyplot as plt


def plot_runtimes(data: dict, title):
    data_to_process = { k:v for k,v in data.items() if v != None }
    names = list(data_to_process.keys())
    values = list(data_to_process.values())

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
    plt.savefig(f"{title}.svg", format='svg')

def main(csv_location):
    groups = {
        "suricata": [],
        "suricata_ensemble": [],
        "snort": [],
        "snort_ensemble": [],
        "slips": [],
        "slips_ensemble": []
    }
    with open(csv_location,encoding="utf-8") as input:
        reader = csv.reader(input)
        header = next(reader)
        for row in reader:
            name = row[0].strip().lower()
            runtime = row[3]
            if "suricata" in name and "snort" not in name and "slips" not in name:
                if "+" in name:
                    groups["suricata_ensemble"].append(float(runtime))
                else:
                    groups["suricata"].append(float(runtime))
            elif "snort" in name and "suricata" not in name and "slips" not in name:
                if "+" in name:
                    groups["snort_ensemble"].append(float(runtime))
                else:
                    groups["snort"].append(float(runtime))            
            elif "slips" in name and "snort" not in name and "suricata" not in name:
                if "+" in name:
                    groups["slips_ensemble"].append(float(runtime))
                else:
                    groups["slips"].append(float(runtime))    
 
    averages = {k: (mean(v) if v else None) for k, v in groups.items()}
    print(averages)
    # print summary
    print("Average analysis times:")
    for k, v in averages.items():
        if v is not None:
            print(f"  {k:<10} {v:>6.2f}s ({len(groups[k]):>2} runs)")

    # build ratio matrix
    methods = [k for k, v in averages.items() if v is not None]

    # determine column width for alignment
    col_width = max(len(m) for m in methods) + 2

    print("\nRelative speed (row vs column, <1 = faster, >1 = slower):\n")

    # header row
    header_row = " " * col_width + "".join(f"{m:>{col_width}}" for m in methods)
    print(header_row)

    for m1 in methods:
        row = f"{m1:<{col_width}}"
        for m2 in methods:
            ratio = averages[m1] / averages[m2] if averages[m1] and averages[m2] else None
            if ratio is None:
                row += f"{'n/a':>{col_width}}"
            else:
                row += f"{ratio:>{col_width}.2f}"
        print(row)

    plot_runtimes(averages, "Average Runtimes (Reduced Dataset)")

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("Wrog ammount of arguments!\nOnly result_csv location is allowed!")
    else:
        main(args[0])
