import csv
import sys
import numpy as np
from statistics import mean

def main(csv_location):
    suricata = []
    snort = []
    slips = []
    with open(csv_location,encoding="utf-8") as input:
        reader = csv.reader(input)
        header = next(reader)
        for row in reader:
            name = row[0].strip().lower()
            runtime = row[3]
            if "suricata" in name and "snort" not in name and "slips" not in name and "+" not in name:
                suricata.append(float(runtime))
            elif "snort" in name and "suricata" not in name and "slips" not in name and "+" not in name:
                snort.append(float(runtime))          
            elif "slips" in name and "snort" not in name and "suricata" not in name and "+" not in name:
                slips.append(float(runtime))
    
    if suricata:
        print(f"Suricata - average analysis time: {mean(suricata)} from {len(suricata)} runs")
    if snort:
        print(f"Snort - average analysis time: {mean(snort)} from {len(snort)} runs")
    if slips:
        print(f"Slips - average analysis time: {mean(slips)} from {len(slips)} runs")

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("Wrog ammount of arguments!\nOnly result_csv location is allowed!")
    else:
        main(args[0])