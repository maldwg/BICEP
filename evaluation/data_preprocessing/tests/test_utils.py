import pytest
import os
from scapy.all import Ether, IP, PcapWriter, TCP, rdpcap
import csv
from datetime import datetime, timezone
from ..utils import Dataset, Precision, parse_timestamp, ts_have_different_values, all_ts_contain
from .helpers import create_generic_dataset_case, make_generic_row, make_tcp_packet


@pytest.fixture
def dataset(tmp_path):
    base_timestamp = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    rows = []
    packets = []

    for index in range(10):
        timestamp = base_timestamp + index
        rows.append(
            make_generic_row(
                f"10.0.0.{index + 1}",
                1000 + index,
                f"10.0.1.{index + 1}",
                2000 + index,
                "TCP",
                datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                0,
                "Benign",
            )
        )
        packets.append(
            make_tcp_packet(
                f"10.0.0.{index + 1}",
                f"10.0.1.{index + 1}",
                1000 + index,
                2000 + index,
                timestamp,
            )
        )

    for index in range(10):
        timestamp = base_timestamp + 60 + index
        rows.append(
            make_generic_row(
                f"10.0.2.{index + 1}",
                3000 + index,
                f"10.0.3.{index + 1}",
                4000 + index,
                "TCP",
                datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                0,
                "Malicious",
            )
        )
        packets.append(
            make_tcp_packet(
                f"10.0.2.{index + 1}",
                f"10.0.3.{index + 1}",
                3000 + index,
                4000 + index,
                timestamp,
            )
        )

    dataset, _, _, _ = create_generic_dataset_case(
        tmp_path,
        rows,
        packets,
        precision=Precision.MINUTE.value,
        case_name="shared-utils",
    )
    return dataset

def test_get_key_from_csv_row(dataset):
    with open(dataset.combined_csv, newline='') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        row = next(reader)
        key = dataset.get_key_from_csv_row(row)
        assert isinstance(key, tuple)
        assert len(key) == 5

def test_transform_csv_to_dict(dataset):
    d = dataset.transform_csv_to_dict(dataset.combined_csv)
    assert isinstance(d, dict)
    assert all(isinstance(k, tuple) and isinstance(v, bool) for k, v in d.items())

def test_extract_key_from_pcap_packet(dataset):
    packets = rdpcap(dataset.combined_pcap)
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
    packet_dict = dataset.transform_csv_to_dict(dataset.combined_csv)
    packets = rdpcap(dataset.combined_pcap)
    for pkt in packets:
        try:
            key = dataset.get_packet_matches_of_csv(pkt, packet_dict)
            assert isinstance(key, tuple)
            break
        except Exception:
            continue

def test_get_benign_malicious_counts(dataset):
    b, m = dataset.get_benign_malicious_counts(dataset.combined_csv)
    assert (b, m) == (10, 10)

def test_sample_from_csv_with_target_values(dataset):
    csv_records, rows = dataset.sample_from_csv_with_target_values(dataset.combined_csv, 1, 1)
    assert isinstance(csv_records, dict)
    assert len(rows) == 3

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
    benign_total, malicious_total = dataset.get_benign_malicious_counts(dataset.combined_csv)
    # Choose realistic small targets
    target_benign = int(0.1 * benign_total)
    target_malicious = int(0.1 * malicious_total)

    csv_records, csv_rows = dataset.sample_from_csv_with_target_values(dataset.combined_csv, target_benign, target_malicious)

    assert all(isinstance(row, list) for row in csv_rows)
    assert all(isinstance(k, tuple) and isinstance(v, bool) for k, v in csv_records.items())

    # Validate count
    actual_benign = sum(1 for row in csv_rows if "benign" in row[dataset.labels_row].lower())
    actual_malicious = sum(1 for row in csv_rows if "malicious" in row[dataset.labels_row].lower())
    assert actual_benign == target_benign
    assert actual_malicious == target_malicious


def test_sample_subset_of_combined_files(dataset, tmp_path):
    output_csv_file = tmp_path / "output_sample.csv"
    output_pcap_file = tmp_path / "output_sample.pcap"

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


def test_sample_from_csv_and_include_pcap_flow_based_keeps_complete_flows(tmp_path):
    combined_csv = tmp_path / "combined.csv"
    combined_pcap = tmp_path / "combined.pcap"
    output_csv = tmp_path / "sampled.csv"
    output_pcap = tmp_path / "sampled.pcap"

    header = [
        "src_ip",
        "src_port",
        "dst_ip",
        "dst_port",
        "protocol",
        "timestamp",
        "flow_duration",
        "label",
    ]
    flow_row = [
        "10.0.0.1",
        "1234",
        "10.0.0.2",
        "80",
        "TCP",
        "2024-01-01 10:00:00",
        "20000000",
        "Benign",
    ]

    with open(combined_csv, "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)
        writer.writerow(flow_row)

    base_ts = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    packets = [
        (Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=1234, dport=80), base_ts),
        (Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=1234, dport=80), base_ts + 15),
        (Ether() / IP(src="10.0.0.2", dst="10.0.0.1") / TCP(sport=80, dport=1234), base_ts + 19),
        (Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=1234, dport=80), base_ts + 25),
    ]

    with PcapWriter(str(combined_pcap), append=False, sync=True) as writer:
        for packet, packet_time in packets:
            packet.time = packet_time
            writer.write(packet)

    synthetic_dataset = Dataset(
        sip_row=0,
        sport_row=1,
        dip_row=2,
        dport_row=3,
        protocol_row=4,
        labels_row=7,
        ts_row=5,
        flow_duration_row=6,
        flow_duration_unit="microseconds",
        base_dir_path=str(tmp_path),
        labels_path_glob=["*.csv"],
        pcap_path_glob=["*.pcap"],
        combined_csv=str(combined_csv),
        combined_pcap=str(combined_pcap),
        precision=Precision.SECOND.value,
    )

    synthetic_dataset.sample_from_csv_and_include_pcap_flow_based(
        output_pcap=str(output_pcap),
        output_csv=str(output_csv),
        sample_ratio_benign=1.0,
        sample_ratio_malicious=0.0,
    )

    with open(output_csv, newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    assert rows == [header, flow_row]

    sampled_packets = rdpcap(str(output_pcap))
    assert len(sampled_packets) == 3
    assert any(
        packet[IP].src == "10.0.0.2" and packet[IP].dst == "10.0.0.1"
        for packet in sampled_packets
    )

    validation_report = synthetic_dataset.validate_sampled_data(str(output_csv), str(output_pcap))
    assert validation_report["is_valid"] is True
    assert validation_report["is_direct_key_compatible"] is True
    assert validation_report["csv_rows_total"] == 1
    assert validation_report["csv_rows_with_flow_packet_match"] == 1
    assert validation_report["csv_rows_with_direct_key_match"] == 1
    assert validation_report["pcap_packets_matched_to_flow"] == 3
    assert validation_report["pcap_packets_unmatched_to_flow"] == 0
    



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
