import pytest
import os
from scapy.all import rdpcap
import csv
from datetime import datetime
from ..utils import Dataset, Precision, parse_timestamp, ts_have_different_values, all_ts_contain

SAMPLE_PCAP = "./evaluation/data_preprocessing/tests/data/sample_data2.pcap"
SAMPLE_CSV = "./evaluation/data_preprocessing/tests/data/sample_data2.csv"

@pytest.fixture
def dataset():
    return Dataset(
        sip_row=1,
        sport_row=2,
        dip_row=3,
        dport_row=4,
        labels_row=-1,
        ts_row=6,
        base_dir_path="./",
        labels_path_glob=["*.csv"],
        pcap_path_glob=["*.pcap"],
        combined_csv=SAMPLE_CSV,
        combined_pcap=SAMPLE_PCAP,
        precision=Precision.MINUTE.value
    )

def test_get_key_from_csv_row(dataset):
    with open(SAMPLE_CSV, newline='') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        row = next(reader)
        key = dataset.get_key_from_csv_row(row)
        assert isinstance(key, tuple)
        assert len(key) == 5

def test_transform_csv_to_dict(dataset):
    d = dataset.transform_csv_to_dict(SAMPLE_CSV)
    with open("./test.json", "w") as f:
        f.write(str(d))
    assert isinstance(d, dict)
    assert all(isinstance(k, tuple) and isinstance(v, bool) for k, v in d.items())
    os.remove("./test.json")

def test_extract_key_from_pcap_packet(dataset):
    packets = rdpcap(SAMPLE_PCAP)
    for pkt in packets:
        try:
            key = dataset.extract_key_from_pcap_packet(pkt)
            assert isinstance(key, tuple)
            assert len(key) == 5
        except Exception:
            continue

def test_get_keys_with_tolerance_second(dataset):
    key = ["2023-01-01 10:00:00", "1.1.1.1", "1234", "2.2.2.2", "80"]
    keys = dataset.get_keys_with_tolerance(key, Precision.SECOND.value, 1)
    for k in keys:
        print(k[0])
    assert keys == [
        ("2023-01-01 09:59:59", '1.1.1.1', '1234', '2.2.2.2', '80'), 
        ("2023-01-01 10:00:00", '1.1.1.1', '1234', '2.2.2.2', '80'), 
        ("2023-01-01 10:00:01", '1.1.1.1', '1234', '2.2.2.2', '80')]


def test_get_keys_with_tolerance_minutes(dataset):
    key = ["2023-01-01 10:00:00", "1.1.1.1", "1234", "2.2.2.2", "80"]
    keys = dataset.get_keys_with_tolerance(key, Precision.MINUTE.value, 1)
    assert keys == [
        ("2023-01-01 09:59", '1.1.1.1', '1234', '2.2.2.2', '80'), 
        ("2023-01-01 10:00", '1.1.1.1', '1234', '2.2.2.2', '80'), 
        ("2023-01-01 10:01", '1.1.1.1', '1234', '2.2.2.2', '80')]


def test_get_packet_matches_of_csv(dataset):
    # use real dictionary from CSV and first PCAP packet
    packet_dict = dataset.transform_csv_to_dict(SAMPLE_CSV)
    packets = rdpcap(SAMPLE_PCAP)
    for pkt in packets:
        try:
            key = dataset.get_packet_matches_of_csv(pkt, packet_dict)
            assert isinstance(key, tuple)
            break
        except Exception:
            continue

def test_get_benign_malicious_counts(dataset):
    b, m = dataset.get_benign_malicious_counts(SAMPLE_CSV)
    assert isinstance(b, int)
    assert isinstance(m, int)
    assert b + m > 0

def test_sample_from_csv_with_target_values(dataset):
    csv_records, rows = dataset.sample_from_csv_with_target_values(SAMPLE_CSV, 1, 1)
    assert isinstance(csv_records, dict)
    assert len(rows) > 0

def test_ts_have_different_values():
    ts_list = ["2023-01-01 10:00:01", "2023-01-01 10:00:02"]
    assert ts_have_different_values(ts_list, Precision.SECOND.value)

def test_all_ts_contain():
    ts_list = ["2023-01-01 10:00:01", "2023-01-01 10:00:02"]
    assert all_ts_contain(ts_list, Precision.SECOND.value)

def test_parse_timestamp():
    ts = "2023-01-01 10:00:01"
    dt = parse_timestamp(ts)
    assert isinstance(dt, datetime)



def test_sample_from_csv_with_target_values_limit(dataset):
    # Read actual counts from the file
    benign_total, malicious_total = dataset.get_benign_malicious_counts(SAMPLE_CSV)
    # Choose realistic small targets
    target_benign = int(0.1 * benign_total)
    target_malicious = int(0.1 * malicious_total)

    csv_records, csv_rows = dataset.sample_from_csv_with_target_values(SAMPLE_CSV, target_benign, target_malicious)

    assert all(isinstance(row, list) for row in csv_rows)
    assert all(isinstance(k, tuple) and isinstance(v, bool) for k, v in csv_records.items())

    # Validate count
    actual_benign = sum(1 for row in csv_rows if "benign" in row[dataset.labels_row].lower())
    actual_malicious = sum(1 for row in csv_rows if "malicious" in row[dataset.labels_row].lower())
    assert actual_benign == target_benign
    assert actual_malicious == target_malicious


def test_sample_subset_of_combined_files(dataset):
    output_csv_file = "output_sample.csv"
    output_pcap_file ="output_sample.pcap"

    dataset.sample_subset_of_combined_files(str(output_pcap_file), str(output_csv_file), ratio=0.1)

    # CSV exists and has rows
    with open(output_csv_file, newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert len(rows) > 1  # header + data
        assert all(len(row) >= 5 for row in rows)

    # PCAP exists and has packets
    packets = rdpcap(str(output_pcap_file))
    assert len(packets) > 0
    os.remove(output_csv_file)
    os.remove(output_pcap_file)
    



# Test for debugging purposes
# def test_pcap_extract_info(dataset):
#     packets = rdpcap(SAMPLE_PCAP)
#     counter = 0
#     key_counter = 0
#     for pkt in packets:
#         info_tuple = dataset.extract_key_from_pcap_packet(pkt)
#         if info_tuple:
#             print(info_tuple)
#             counter += 1
#             keys = dataset.get_keys_with_tolerance(info_tuple, precision=Precision.MINUTE.value)
#             print(keys)
#             if len(keys) > 0:
#                 key_counter += 1
#     print(counter)
#     print(key_counter)
    

#     assert False

# Test for debugging purposes
# def test_pcap_with_csv(dataset):
#     output_csv_file = "output_sample.csv"
#     output_pcap_file ="output_sample.pcap"
#     assignable, unassignable = dataset.test_pcap_against_csv(output_pcap_file, output_csv_file)
#     print(f"Got {assignable} assignable, {unassignable} unassignable packets. Ratio: {assignable/unassignable}")
#     assert False
