import csv
import sys
import numpy as np
from statistics import mean

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

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("Wrog ammount of arguments!\nOnly result_csv location is allowed!")
    else:
        main(args[0])
