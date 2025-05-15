import csv
from datetime import datetime, timedelta
import os
import tempfile

# === USER CONFIGURATION SECTION ===

# CSV input file paths (these will be overwritten)
CPU_CSV = "./snort/CPU Consumption-data-2025-05-15 17_14_22.csv"
MEM_CSV = "./snort/Memory Consumption-data-2025-05-15 17_14_16.csv"

# List of (start_time, end_time) tuples in ISO 8601 format
TIMEFRAMES = [
    ("2025-05-15T17:11:31.604972","2025-05-15T17:11:37.809111"),
    ("2025-05-15T17:12:17.675941","2025-05-15T17:12:23.337351"),
    ("2025-05-15T17:13:11.593978","2025-05-15T17:13:18.023187")
]

# Margin in seconds to extend the timeframes
MARGIN_SECONDS = 4

# === END USER CONFIGURATION ===


def parse_timeframe_list(timeframe_list, margin_seconds):
    """Parse timeframes into datetime tuples with margin applied."""
    parsed = []
    for start_str, end_str in timeframe_list:
        start = datetime.fromisoformat(start_str) - timedelta(seconds=margin_seconds)
        end = datetime.fromisoformat(end_str) + timedelta(seconds=margin_seconds)
        parsed.append((start, end))
    return parsed


def is_in_timeframes(timestamp: datetime, timeframes: list) -> bool:
    """Check if timestamp is within any of the timeframes."""
    return any(start <= timestamp <= end for start, end in timeframes)


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
                timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue  # Skip malformed rows

            if is_in_timeframes(timestamp, timeframes):
                writer.writerow(row)

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
