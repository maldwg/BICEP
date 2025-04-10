import os
import glob
from scapy.all import PcapReader, PcapWriter
import random 
import os.path
import csv
from scapy.all import PcapReader
import pandas as pd
from datetime import datetime
from tqdm import tqdm
from dateutil import parser 
from ..utils import *

CTU13_BASE_DIR = "/home/sftpuser/uploads/master/CTU-13/CTU-13-Dataset/"
CTU13_LABELS_GLOB = "*/*.binetflow"
CTU13_PCAP_GLOB = "*/*.pcap"
CTU13_COMBINED_CSV = "./combined_ctu13.csv"
CTU13_COMBINED_PCAP = "./combined_ctu13.pcap"

def convert_binetflow_to_csv_and_combine(label_glob_pattern, output_path):
    """
    Converts multiple .binetflow files into CSV format and combines them.

    Args:
        label_glob_pattern (str): Glob pattern to find .binetflow files.
        output_path (str): Path to output the combined CSV.

    Returns:
        None
    """
    full_pattern = os.path.join(CTU13_BASE_DIR, label_glob_pattern)
    label_files = sorted(glob.glob(full_pattern))
    print(f"Found {len(label_files)} binetflow files")

    header_written = False
    with open(output_path, "w", newline="") as combined_csv:
        writer = csv.writer(combined_csv)
        for path in label_files:
            print(f"Processing binetflow: {path}")
            with open(path, "r") as f:
                reader = csv.reader(f)
                header = next(reader)
                if not header_written:
                    writer.writerow(header)
                    header_written = True

                for row in reader:
                    corrected_row = correct_csv_row(row)
                    writer.writerow(corrected_row)
    print(f"Combined binetflow CSV written to {output_path}")


def correct_csv_row(row):
    """
    Corrects a single row in the UNSW-NB15 CSV file.

    Args:
        row (List[str]): A row from the CSV file.

    Returns:
        List[str]: The corrected CSV row.
    """
    corrected_row = row
    if "Normal" in row[-1] or "Background" in row[-1]:
        corrected_row[-1] = "Benign"
    else:
        corrected_row[-1] = "Malicious"
    start_time = parser.parse(row[0], dayfirst=False).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    corrected_row[0] = start_time 
    return corrected_row


def combine_ctu13_pcaps(pcap_glob_pattern, output_path):
    """
    Combines multiple CTU-13 PCAP files into one.

    Args:
        pcap_glob_pattern (str): Glob pattern for locating PCAP files.
        output_path (str): Output PCAP path.

    Returns:
        None
    """
    files = glob.glob(os.path.join(CTU13_BASE_DIR, pcap_glob_pattern))
    if not files:
        print("No pcap files found.")
        return

    with PcapWriter(output_path, append=True) as writer:
        for file in files:
            print(f"Reading: {file}")
            with PcapReader(file) as reader:
                for pkt in tqdm(reader, desc=f"Processing {os.path.basename(file)}"):
                    writer.write(pkt)
    print(f"Combined PCAP written to {output_path}")

def sample_ctu13_csv(pcap_path, pcap_output_path, csv_output_path, csv_path, sample_size=5000):
    """
    Samples a balanced subset of CTU-13 CSV by label.

    Args:
        input_path (str): Path to combined CSV.
        output_path (str): Where to save the sampled CSV.
        label_column (str): Label column name.
        sample_size (int): Number of rows to sample.
        random_seed (int): Seed for reproducibility.

    Returns:
        None
    """
    print(f"Sampling {sample_size} from {pcap_path}...")
    samples = []
    with PcapWriter(pcap_output_path, append=False) as pcap_writer:
        with PcapReader(pcap_path) as reader:
            for i, pkt in enumerate(reader):
                samples.append(pkt)
                pcap_writer.write(pkt)
                if len(samples) >= sample_size:
                    break
    print(f"Extracted {len(samples)} packets.")

    print(f"Loading CSV {csv_path}...")
    csv_records = transform_csv_to_dict(csv_path)

    print("Filtering CSV...")
    matches = {}
    for pkt in tqdm(samples, total=sample_size, desc="Sampling process"):
        match = get_packet_matches_of_csv(pkt, csv_records)
        if match:
            matches[match] = True

    if matches:
        matching_rows = 0
        with open(output_csv, "w") as sampled_csv:
            writer = csv.writer(sampled_csv)
            with open(csv_path, "r") as input_csv:
                reader = csv.reader(input_csv)
                header = next(reader)
                writer.writerow(header)
                for row in reader:
                    key = get_key_from_csv_row(row)
                    if key in matches:
                        writer.writerow(row)
                        matching_rows += 1
        print(f"Found {matching_rows} matching rows.")
        print(f"Filtered CSV written to: {output_csv}")
    else:
        print("No matches found.")


if __name__ == "__main__":
    # convert_binetflow_to_csv_and_combine(CTU13_LABELS_GLOB, CTU13_COMBINED_CSV)
    combine_ctu13_pcaps(CTU13_PCAP_GLOB, CTU13_COMBINED_PCAP)
    # sample_ctu13_csv("./ctu13_labeled.csv", "./ctu13_sampled.csv", sample_size=5000)


