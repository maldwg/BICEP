import csv
from datetime import datetime, timedelta
import os
import tempfile
from dateutil import parser

# CSV input file paths (these will be overwritten)
CPU_CSV = "./snort/CPU Consumption-balanced-red.csv"
MEM_CSV = "./snort/Memory Consumption-balanced-red.csv"

# List of (start_time, end_time) tuples in ISO 8601 format
TIMEFRAMES = [
    ("2025-05-21 12:34:10","2025-05-21 12:34:18"),
    ("2025-05-21 12:37:43","2025-05-21 12:37:44"),
    ("2025-05-21 12:39:33","2025-05-21 12:39:35")

]

# Margin in seconds to extend the timeframes
MARGIN_SECONDS = 4


def parse_timeframe_list(timeframe_list, margin_seconds):
    """Parse timeframes using dateutil parser with margin and return datetime tuples."""
    parsed = []
    for start_str, end_str in timeframe_list:
        start = parser.parse(start_str) - timedelta(seconds=margin_seconds) + timedelta(hours=2)
        end = parser.parse(end_str) + timedelta(seconds=margin_seconds) + timedelta(hours=2)
        parsed.append((start, end))
    return parsed

def is_in_timeframes(timestamp: str, timeframes: list) -> bool:
    """Check if a timestamp string is within any of the parsed timeframes."""
    ts = parser.parse(timestamp)
    return any(start <= ts <= end for start, end in timeframes)


def filter_csv_in_place(file_path: str, timeframes: list):
    """Filter a CSV file in-place to keep only rows within given timeframes."""
    temp_fd, temp_path = tempfile.mkstemp()

    with open(file_path, newline='') as infile, open(temp_path, 'w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        header = next(reader)
        writer.writerow(header)

        for row in reader:
            try:
                timestamp = row[0]
                if is_in_timeframes(timestamp, timeframes):
                    writer.writerow(row)
            except:
                continue
    os.close(temp_fd)
    os.replace(temp_path, file_path)


def main():
    timeframes = parse_timeframe_list(TIMEFRAMES, MARGIN_SECONDS)

    print(f"Filtering {CPU_CSV} and {MEM_CSV} for {len(timeframes)} timeframes...")

    filter_csv_in_place(CPU_CSV, timeframes)
    filter_csv_in_place(MEM_CSV, timeframes)

    print("Done. Files updated in place.")


if __name__ == '__main__':
    main()
