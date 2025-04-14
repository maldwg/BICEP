"""
Methods to take the original dataset as input and adapt the timestamps in the CSVs to be of the correct format
"""

import csv
from datetime import datetime, timedelta
from dateutil import parser


# Change this to the desired locations
input_csv_file = "/mnt/d/master/Wednesday-WorkingHours.pcap_ISCX.csv"
output_csv_file = "/mnt/d/master/Wednesday-WorkingHours_newly_corrected.csv"


def adjust_time_to_24_hour_format(csv_time):
    hour = csv_time.hour
    if 1 <= hour <= 7:
        csv_time = csv_time + timedelta(hours=12)
    return csv_time


# use dateutils parser instead...
def parse_timestamp(timestamp_str):
    # List of possible formats
    formats = [
        "%d/%m/%Y %H:%M:%S",  # e.g., 04/07/2017 08:54:12
        "%d/%m/%Y %-H:%M:%S", # e.g., 04/07/2017 8:54:12
        "%-d/%-m/%Y %H:%M:%S"  # e.g., 4/07/2017 08:54:12
        "%-d/%-m/%Y %-H:%M:%S", # e.g., 4/7/2017 8:54:12
        "%d/%m/%Y %H:%M",     # e.g., 04/07/2017 08:54
        "%-d/%-m/%Y %-H:%M",   # e.g., 4/7/2017 8:54

    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Time data '{timestamp_str}' does not match any expected formats.")





print(output_csv_file)
updated_rows = []
with open(output_csv_file, 'w', newline='') as output_csv:
    writer = csv.writer(output_csv)
    with open(input_csv_file, 'r') as input_csv:
        reader = csv.reader(input_csv)
        header = next(reader)  
        writer.writerow(header)
        
        for row in reader:
            csv_time_cell = row[6]  
            csv_time = parser.parse(csv_time_cell,dayfirst=True).replace(tzinfo=None)
            csv_time = adjust_time_to_24_hour_format(csv_time)
            row[6] = csv_time.isoformat()             
            writer.writerow(row)

print(f"Timestamps in {input_csv_file} have been adjusted and written to {output_csv_file}.")

