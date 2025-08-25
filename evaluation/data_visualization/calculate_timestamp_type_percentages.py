import csv
import sys
import glob
from dateutil import parser 
import re
from tqdm import tqdm
from datetime import datetime



def classify_precision(ts: str) -> str:
    """Classify timestamp precision by counting colons and checking for fractions."""
    ts = ts.strip()
    if not ts:
        return "hour"

    # take only the time part if a date is present
    if " " in ts:
        ts = ts.split()[-1]
    if "T" in ts:  # ISO style
        ts = ts.split("T")[-1]

    colon_count = ts.count(":")

    if colon_count == 0:
        return "hour"
    elif colon_count == 1:
        return "minute"
    elif colon_count == 2:
        if "." in ts:
            return "millisecond"
        else:
            return "second"
    else:
        return "hour"  # fallback

def calculate_percentages(ts_row, files):
    totals = {"total": 0, "millisecond": 0, "second": 0, "minute": 0, "hour": 0}

    unsw_dataset = any("UNSW" in file for file in files)
    for file in files:
        print(f"Now addressing {file}...")
        with open(file, encoding="utf-8",  errors="replace") as csv_file:
            reader = csv.reader(csv_file)
            header = next(reader)
            for row in tqdm(reader):
                try: 
                    timestamp = row[ts_row].strip()
                    if unsw_dataset:
                        timestamp = int(row[ts_row])
                        timestamp = datetime.fromtimestamp(timestamp).isoformat()
                    if not timestamp:
                        continue
                    bucket = classify_precision(timestamp)
                    totals["total"] += 1
                    totals[bucket] += 1

                except:
                    continue
                                    
    return totals
    
def visualize_percentages(stats):
    print(stats)
    labels = [("Hour", "hour"), ("Minute", "minute"),
              ("Second", "second"), ("Millisecond", "millisecond")]
    total = stats["total"]
    lines = []
    lines.append(f"{'Precision':<15}{'Count':>10}{'Percent':>12}")
    lines.append("-" * 37)
    for label, key in labels:
        count = stats[key]
        pct = (count / total * 100) if total else 0
        lines.append(f"{label:<15}{count:>10}{pct:>11.2f}%")
    lines.append("-" * 37)
    lines.append(f"{'Total':<15}{total:>10}{'100.00%' if total else '0.00%':>12}")
    print("\n".join(lines))
            
def main(dataset_name, dataset_location):
    files = []
    ts_row = None
    match dataset_name:
        case "CICIDS":
           files.extend(glob.glob(f"{dataset_location}/*.csv")) 
           ts_row = 6
        case "UNSWNB15":
            files.extend(glob.glob(f"{dataset_location}/UNSW-NB15_[1-4].csv")) 
            ts_row = 28
        case "CTU13":
            files.extend(glob.glob(f"{dataset_location}/*/*.binetflow")) 
            ts_row = 0
    if files == []:
        print("No files found!\n Maybe wrong dataset name or location provided?")
    else:
        print(f"Start analysis of {dataset_name}")
        percentages = calculate_percentages(ts_row, files)
        visualize_percentages(percentages)

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 2:
        print("Too many arguments")
    elif len(args) == 0:
        print("Dataset-name and location missing! \nChoose one of: CICIDS, UNSWNB15, CTU13")
    elif ["help", "-h"] in args: 
        print("example usage: python3 calculate_timestamp_type_percentages.py CTU13 <dir_containing_labels_files>")
    else: 
        main(dataset_name=args[0],dataset_location=args[1])

    # usage:    python3 calculate_timestamp_type_percentages.py CICIDS "/mnt/hdd/Datasets/CIC-IDS-2017/default-labels-files"
    #           python3 calculate_timestamp_type_percentages.py UNSWNB15 "/mnt/hdd/Datasets/unsw-nb15/labels"
    #           python3 calculate_timestamp_type_percentages.py CTU13 "/mnt/hdd/Datasets/CTU-13"