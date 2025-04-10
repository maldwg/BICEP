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


BASE_DIR = "/home/sftpuser/uploads/master/unsw-nb15/"
FEATURE_NAMES_FILE = "labels/NUSW-NB15_features.csv"
LABELS_PATH = [ 
    "labels/UNSW-NB15_1.csv", 
    "labels/UNSW-NB15_2.csv", 
    "labels/UNSW-NB15_3.csv", 
    "labels/UNSW-NB15_4.csv" 
]
PCAP_PATH_PATTERN = [ 
    "pcaps/1/*.pcap", 
    "pcaps/2/*.pcap" 
]

# Output paths
LABELS_FILES = [ os.path.join(BASE_DIR, file) for file in LABELS_PATH]
COMBINED_CSV = "./combined.csv" 
COMBINED_PCAP = "./combined.pcap"


def combine_csvs(csv_paths, feature_names_csv, output_path):
    # ensure that header get processed too
    header_values = []
    csv_paths.insert(0, os.path.join(BASE_DIR, feature_names_csv))

    with open(output_path, "w", newline="", encoding="utf-8") as output_csv:
        writer = csv.writer(output_csv) 
        for path in csv_paths:
            print(f"Now processing {path}")
            with open(path, "r", encoding="latin1") as input_csv:
                reader = csv.reader(input_csv)
                if not header_values:
                    print("Discovered header not included yet...")
                    # skip header
                    _header = next(reader)
                    for row in reader:
                        feature_name = row[1]
                        header_values.append(feature_name)
                    writer.writerow(header_values)
                else:
                    for row in reader:
                        corrected_row = correct_csv_row(row)
                        writer.writerow(corrected_row)
    print(f"Combined CSV written to {output_path}")


def test_pcap_against_csv(pcap_glob_patterns, csv_path):
    """ethod to check if pcap and csv are correlating at all"""
    test_files = []
    for pattern in pcap_glob_patterns:
        full_pattern = os.path.join(BASE_DIR, pattern)
        test_files.extend(glob.glob(full_pattern))
    if not test_files:
        print("No pcap files found for testing.")
        return

    test_file = random.choice(test_files)
    print(f"Testing pcap file: {test_file}")

    df = pd.read_csv(csv_path, encoding="latin1")
    print(f"Loaded {len(df)} rows from CSV")
    assignable = 0
    unassignable = 0
    print("Iterating over the pcap...")
    with PcapReader(test_file) as reader:
        number_of_packets = 0
        for pkt in tqdm(reader, desc="Processing packets"):
            number_of_packets += 1
            if get_packet_matches_of_csv(pkt, df):
                assignable += 1
            else:
                unassignable += 1
            
    print("Done testing pcap vs CSV")
    print(f"PCAP got {number_of_packets} packets")
    print(f"Got {assignable} assignable, {unassignable} unassignable packets. Ratio: {assignable/unassignable}")

def combine_pcaps(pcap_globs, output_pcap_path):
    with PcapWriter(output_pcap_path, append=True) as writer:
        for pattern in pcap_globs:
            files = glob.glob(os.path.join(BASE_DIR, pattern))
            for pcap_file in files:
                print(f"Reading from {pcap_file}")
                with PcapReader(pcap_file) as reader:
                    for packet in tqdm(reader, desc=f"Packets of file {pcap_file}"):                        
                        writer.write(packet)
    print(f"Combined pcap written to {output_pcap_path}")


def get_packet_matches_of_csv(pkt, csv_records, time_margin=0.5):
    key = extract_key_from_pcap_packet(pkt)
    if key:
        if key in csv_records:
            print("key existing in csv")
            print(key)
            return key
        else:
            print("key found but not in records")
            print(key)
    else:
        print("key-not-found")
        print(key)
        return None
        
def sample_pcap_and_filter_csv(pcap_path, pcap_output_path, csv_path, output_csv, sample_size=10000):
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

def count_pcap_packets(pcap_path):
    count = 0
    with PcapReader(pcap_path) as reader:
        for _ in reader:
            count += 1
    return count


def get_key_from_csv_row(row):
    src_ip = str(row[0])
    src_port = str(row[1])
    dest_ip = str(row[2])
    dest_port = str(row[3])
    try:
        timestamp = datetime.fromtimestamp(row[28]).strftime("%Y-%m-%d %H:%M:%S") 
    except Exception as e:
        timestamp = parser.parse(row[28], dayfirst=False).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
    key = (timestamp, src_ip, src_port, dest_ip, dest_port)
    return key

def extract_key_from_pcap_packet(pkt):
    try:
        if pkt.haslayer("IP") or pkt.haslayer("IPv6"):
            ip_layer = pkt["IP"] if pkt.haslayer("IP") else pkt["IPv6"]
            transport = pkt.getlayer("TCP") or pkt.getlayer("UDP")
            if transport:
                timestamp = timestamp = datetime.fromtimestamp(float(pkt.time)).strftime("%Y-%m-%d %H:%M:%S") 
                srcip = str(ip_layer.src)
                sport = str(transport.sport)
                dstip = str(ip_layer.dst)
                dsport = str(transport.dport)
                return (timestamp, srcip, sport, dstip, dsport)
    except Exception as e:
        pass
    return None

def transform_csv_to_dict(csv_path):
    csv_records = {}
    with open(csv_path, 'r') as input_csv:
        reader = csv.reader(input_csv)
        # skip header
        _ = next(reader)
        for row in reader:
            key = get_key_from_csv_row(row)
            csv_records[key] = True
    return csv_records

def correct_csv_row(row):
    corrected_row = row
    if row[-1] == 0:
        corrected_row[-1] = "Benign"
    else:
        corrected_row[-1] = "Malicious"
    start_time_human_readable = datetime.fromtimestamp(int(row[28])).strftime("%Y-%m-%d %H:%M:%S")
    corrected_row[28] = start_time_human_readable 
    return corrected_row


def correct_pcap_packet():
    pass



if __name__ == "__main__":
    # combine_csvs(LABELS_FILES, FEATURE_NAMES_FILE, COMBINED_CSV)
    # combine_pcaps(["CIC-IDS-2017/sample_data2.pcap", "CIC-IDS-2017/sample_data2.pcap" ], COMBINED_PCAP)
    # combine_pcaps(PCAP_PATH_PATTERN, COMBINED_PCAP)

    all_pcap_files = []
    full_pattern = os.path.join(BASE_DIR, PCAP_PATH_PATTERN[0])
    all_pcap_files.extend(glob.glob(full_pattern))

    sample_pcap_and_filter_csv(
        pcap_output_path="sample_1000.pcap",
        pcap_path=random.choice(all_pcap_files),
        csv_path="combined.csv",
        output_csv="sample_1000.csv",
        sample_size=1000
    )
#
    ## test_pcap_against_csv("sample_10000.pcap", COMBINED_CSV)
