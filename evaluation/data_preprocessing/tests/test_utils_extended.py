import csv
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from scapy.all import Dot1Q, Ether, IP, IPv6, Raw, TCP, UDP, rdpcap

from .helpers import (
    create_generic_dataset_case,
    make_generic_row,
    make_ipv6_udp_packet,
    make_tcp_packet,
    make_udp_packet,
)
from .. import utils as utils_module
from ..utils import (
    Dataset,
    Precision,
    csv_row_is_empty,
    extract_transport_tuple_from_packet_bytes,
    get_length_of_pcap,
    normalize_protocol_value,
    normalize_timestamp,
    parse_ipv4_transport_tuple,
    parse_ipv6_transport_tuple,
)


def test_normalize_protocol_value_handles_aliases_numbers_and_blanks():
    assert normalize_protocol_value("TCP") == "6"
    assert normalize_protocol_value("17") == "17"
    assert normalize_protocol_value("17.0") == "17"
    assert normalize_protocol_value("") is None
    assert normalize_protocol_value(None) is None


@pytest.mark.parametrize(
    ("unit", "raw_value", "expected"),
    [
        ("seconds", "2", 2.0),
        ("milliseconds", "2500", 2.5),
        ("microseconds", "2500000", 2.5),
        ("nanoseconds", "2500000000", 2.5),
    ],
)
def test_get_flow_duration_seconds_supports_declared_units(tmp_path, unit, raw_value, expected):
    row = make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", "2024-01-01 12:00:00", raw_value, "Benign")
    dataset, _, _, _ = create_generic_dataset_case(
        tmp_path,
        [row],
        [],
        case_name=f"duration_{unit}",
        extra_dataset_kwargs={"flow_duration_unit": unit},
    )

    assert dataset.get_flow_duration_seconds(row) == pytest.approx(expected)


def test_get_precision_window_and_timestamp_normalization(tmp_path):
    row = make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", "2024-01-01 12:00:05", 0, "Benign")
    dataset, _, _, _ = create_generic_dataset_case(tmp_path, [row], [], case_name="precision")

    assert dataset.get_precision_window() == timedelta(seconds=1)
    assert normalize_timestamp(datetime(2024, 1, 1, 12, 0, 5, 123456), Precision.SECOND.value) == "2024-01-01 12:00:05"
    assert normalize_timestamp(datetime(2024, 1, 1, 12, 0, 5, 123456), Precision.MINUTE.value) == "2024-01-01 12:00"


def test_bidirectional_flow_keys_and_windows_are_direction_agnostic(tmp_path):
    early_row = make_generic_row("10.0.0.2", 80, "10.0.0.1", 1234, "TCP", "2024-01-01 12:00:00", 5_000_000, "Benign")
    late_row = make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", "2024-01-01 12:00:10", 5_000_000, "Benign")
    dataset, _, _, _ = create_generic_dataset_case(tmp_path, [late_row, early_row], [], case_name="windows")

    assert dataset.get_bidirectional_flow_key("10.0.0.1", 1234, "10.0.0.2", 80) == dataset.get_bidirectional_flow_key(
        "10.0.0.2", 80, "10.0.0.1", 1234
    )

    window = dataset.build_flow_window_from_csv_row(early_row, row_index=0)
    assert window.start == datetime(2024, 1, 1, 12, 0, 0)
    assert window.end == datetime(2024, 1, 1, 12, 0, 6)

    flow_lookup = dataset.build_flow_lookup([late_row, early_row])
    stored_windows = next(iter(flow_lookup.values()))
    assert [item.start for item in stored_windows] == [
        datetime(2024, 1, 1, 12, 0, 0),
        datetime(2024, 1, 1, 12, 0, 10),
    ]


def test_get_matching_flow_windows_filters_on_time_and_protocol(tmp_path):
    row = make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", "2024-01-01 12:00:00", 4_000_000, "Benign")
    dataset, _, _, _ = create_generic_dataset_case(tmp_path, [row], [], case_name="match_windows")
    flow_lookup = dataset.build_flow_lookup([row])

    matching_metadata = {
        "flow_key": dataset.get_bidirectional_flow_key("10.0.0.2", 80, "10.0.0.1", 1234),
        "protocol": "6",
        "timestamp": datetime(2024, 1, 1, 12, 0, 3),
    }
    protocol_mismatch = dict(matching_metadata, protocol="17")
    time_mismatch = dict(matching_metadata, timestamp=datetime(2024, 1, 1, 12, 0, 10))

    assert len(dataset.get_matching_flow_windows(matching_metadata, flow_lookup)) == 1
    assert dataset.get_matching_flow_windows(protocol_mismatch, flow_lookup) == []
    assert dataset.get_matching_flow_windows(time_mismatch, flow_lookup) == []


def test_transport_tuple_helpers_parse_ipv4_and_ipv6_packets():
    ipv4_packet = bytes(Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=1234, dport=80) / Raw(b"x"))
    ipv6_packet = bytes(Ether() / IPv6(src="2001:db8::1", dst="2001:db8::2") / UDP(sport=5555, dport=53) / Raw(b"x"))
    arp_packet = bytes(Ether() / Raw(b"\x00" * 20))

    assert parse_ipv4_transport_tuple(ipv4_packet, 14) == ("10.0.0.1", 1234, "10.0.0.2", 80, 6)
    assert parse_ipv6_transport_tuple(ipv6_packet, 14) == ("2001:db8::1", 5555, "2001:db8::2", 53, 17)
    assert extract_transport_tuple_from_packet_bytes(ipv4_packet) == ("10.0.0.1", 1234, "10.0.0.2", 80, 6)
    assert extract_transport_tuple_from_packet_bytes(ipv6_packet) == ("2001:db8::1", 5555, "2001:db8::2", 53, 17)
    assert extract_transport_tuple_from_packet_bytes(arp_packet) is None


def test_extract_flow_metadata_from_raw_packet_supports_ipv4_and_ipv6(tmp_path):
    row = make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", "2024-01-01 12:00:00", 0, "Benign")
    dataset, _, _, _ = create_generic_dataset_case(tmp_path, [row], [], case_name="raw_metadata")
    metadata = SimpleNamespace(sec=1_704_110_400, usec=250_000)

    ipv4_bytes = bytes(Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=1234, dport=80) / Raw(b"x"))
    ipv6_bytes = bytes(Ether() / IPv6(src="2001:db8::1", dst="2001:db8::2") / UDP(sport=5555, dport=53) / Raw(b"x"))

    ipv4_flow = dataset.extract_flow_metadata_from_raw_packet(ipv4_bytes, metadata)
    ipv6_flow = dataset.extract_flow_metadata_from_raw_packet(ipv6_bytes, metadata)

    assert ipv4_flow["protocol"] == "6"
    assert ipv4_flow["timestamp"] == datetime.fromtimestamp(1_704_110_400.25, timezone.utc).replace(tzinfo=None)
    assert ipv6_flow["protocol"] == "17"

    forward_key, reverse_key = dataset.extract_keys_from_raw_packet(ipv4_bytes, metadata)
    assert forward_key == ("2024-01-01 12:00:00", "10.0.0.1", "1234", "10.0.0.2", "80")
    assert reverse_key == ("2024-01-01 12:00:00", "10.0.0.2", "80", "10.0.0.1", "1234")


def test_transport_tuple_helpers_cover_edge_cases_and_non_matches(tmp_path):
    row = make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", "2024-01-01 12:00:00", 0, "Benign")
    dataset, _, _, _ = create_generic_dataset_case(tmp_path, [row], [], case_name="transport_edges", precision=Precision.HOUR.value)
    metadata = SimpleNamespace(sec=1_704_110_400, usec=0)

    vlan_ipv4 = bytes(Ether() / Dot1Q(vlan=7) / IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=1234, dport=80) / Raw(b"x"))
    cooked_ipv4 = b"\x00" * 14 + b"\x08\x00" + bytes(IP(src="10.0.0.3", dst="10.0.0.4") / TCP(sport=5555, dport=443) / Raw(b"x"))
    cooked_ipv6 = b"\x00" * 14 + b"\x86\xdd" + bytes(IPv6(src="2001:db8::1", dst="2001:db8::2") / UDP(sport=9999, dport=53) / Raw(b"x"))
    ipv4_with_unsupported_proto = bytes(Ether() / IP(src="10.0.0.5", dst="10.0.0.6", proto=1) / Raw(b"x"))
    ipv6_without_transport = bytes(Ether() / IPv6(src="2001:db8::3", dst="2001:db8::4") / Raw(b"x"))

    assert parse_ipv4_transport_tuple(b"\x00" * 10, 0) is None
    assert parse_ipv4_transport_tuple(bytes(IPv6(src="2001:db8::1", dst="2001:db8::2")), 0) is None
    assert parse_ipv4_transport_tuple(ipv4_with_unsupported_proto[14:], 0) is None
    assert parse_ipv6_transport_tuple(b"\x00" * 10, 0) is None
    assert parse_ipv6_transport_tuple(bytes(IP(src="10.0.0.1", dst="10.0.0.2")), 0) is None
    assert parse_ipv6_transport_tuple(ipv6_without_transport[14:], 0) is None
    assert extract_transport_tuple_from_packet_bytes(b"\x00" * 10) is None
    assert extract_transport_tuple_from_packet_bytes(vlan_ipv4) == ("10.0.0.1", 1234, "10.0.0.2", 80, 6)
    assert extract_transport_tuple_from_packet_bytes(cooked_ipv4) == ("10.0.0.3", 5555, "10.0.0.4", 443, 6)
    assert extract_transport_tuple_from_packet_bytes(cooked_ipv6) == ("2001:db8::1", 9999, "2001:db8::2", 53, 17)
    assert dataset.extract_flow_metadata_from_raw_packet(b"\x00" * 10, metadata) is None
    assert dataset.get_precision_window() == timedelta(hours=1)


def test_sample_random_csv_rows_and_lines_are_deterministic_with_monkeypatched_sampling(tmp_path, monkeypatch):
    rows = [
        make_generic_row("10.0.0.1", 1000 + index, "10.0.0.2", 80, "TCP", f"2024-01-01 12:00:{index:02d}", 0, "Benign")
        for index in range(4)
    ]
    rows.extend(
        make_generic_row("10.0.1.1", 2000 + index, "10.0.1.2", 443, "TCP", f"2024-01-01 12:01:{index:02d}", 0, "Malicious")
        for index in range(10)
    )
    dataset, _, _, case_dir = create_generic_dataset_case(tmp_path, rows, [], case_name="random_sampling")

    monkeypatch.setattr(utils_module.random, "randint", lambda _start, end: end)

    header, sampled_rows = dataset.sample_random_csv_rows(sample_ratio_benign=0.5, sample_ratio_malicious=0.5)
    benign_rows = [row for row in sampled_rows if row[-1] == "Benign"]
    malicious_rows = [row for row in sampled_rows if row[-1] == "Malicious"]
    assert header[0] == "src_ip"
    assert len(benign_rows) == 2
    assert len(malicious_rows) == 6

    output_csv = case_dir / "sampled.csv"
    written_rows = dataset.sample_random_csv_lines(0.5, 0.5, str(output_csv))
    with open(output_csv, newline="") as csv_file:
        output = list(csv.reader(csv_file))
    assert len(written_rows) == 8
    assert len(output) == 9


def test_get_packet_matches_reverse_included_and_exact_target_sampling(tmp_path):
    matching_row = make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", "2024-01-01 12:00:00", 0, "Benign")
    malicious_row = make_generic_row("10.0.0.3", 4321, "10.0.0.4", 443, "TCP", "2024-01-01 12:00:01", 0, "Malicious")
    reverse_packet = make_tcp_packet("10.0.0.2", "10.0.0.1", 80, 1234, datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp())
    dataset, _, _, _ = create_generic_dataset_case(tmp_path, [matching_row, malicious_row], [reverse_packet], case_name="reverse_match")

    csv_records = dataset.transform_csv_to_dict(dataset.combined_csv)
    assert dataset.get_packet_matches_of_csv_reverse_packets_included(reverse_packet, csv_records, dataset.precision) is not None

    sampled_records, sampled_rows = dataset.sample_from_csv_with_target_values(dataset.combined_csv, 1, 1)
    assert len(sampled_records) == 2
    assert sum(1 for row in sampled_rows[1:] if row[-1] == "Benign") == 1
    assert sum(1 for row in sampled_rows[1:] if row[-1] == "Malicious") == 1


def test_sample_from_csv_and_include_pcap_flow_based_produces_outputs(tmp_path):
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    rows = []
    packets = []
    for index in range(6):
        timestamp = datetime.fromtimestamp(base_time + index, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        rows.append(make_generic_row("10.0.0.1", 1234 + index, "10.0.0.2", 80, "TCP", timestamp, 0, "Benign"))
        packets.append(make_tcp_packet("10.0.0.1", "10.0.0.2", 1234 + index, 80, base_time + index))

    dataset, _, _, case_dir = create_generic_dataset_case(tmp_path, rows, packets, case_name="pcap_filter")
    output_pcap = case_dir / "filtered.pcap"
    output_csv = case_dir / "filtered.csv"

    dataset.sample_from_csv_and_include_pcap_flow_based(
        str(output_pcap),
        str(output_csv),
        sample_ratio_benign=0.5,
        sample_ratio_malicious=0.5,
    )

    assert output_pcap.exists()
    assert output_csv.exists()
    assert len(rdpcap(str(output_pcap))) > 0
    with open(output_csv, newline="") as csv_file:
        output_rows = list(csv.reader(csv_file))
    assert len(output_rows) > 1

    validation_report = dataset.validate_sampled_data(str(output_csv), str(output_pcap))
    assert validation_report["is_valid"] is True
    assert validation_report["is_direct_key_compatible"] is True
    assert validation_report["csv_rows_without_flow_packet_match"] == 0
    assert validation_report["csv_rows_without_direct_key_match"] == 0
    assert validation_report["pcap_packets_unmatched_to_flow"] == 0


def test_validate_sampled_data_detects_misaligned_outputs(tmp_path):
    row = make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", "2024-01-01 12:00:00", 0, "Benign")
    packet = make_tcp_packet("10.0.0.9", "10.0.0.10", 9999, 443, datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc).timestamp())
    dataset, _, _, case_dir = create_generic_dataset_case(tmp_path, [row], [packet], case_name="validation_failure")

    invalid_report = dataset.validate_sampled_data(raise_on_failure=False)
    assert invalid_report["is_valid"] is False
    assert invalid_report["is_direct_key_compatible"] is False
    assert invalid_report["csv_rows_without_flow_packet_match"] == 1
    assert invalid_report["csv_rows_without_direct_key_match"] == 1
    assert invalid_report["pcap_packets_unmatched_to_flow"] == 1

    with pytest.raises(AssertionError, match="Unmatched CSV rows"):
        dataset.validate_sampled_data()


def test_get_sample_rows_precision_noise_and_ratio_writers(tmp_path):
    base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    rows = [
        make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", f"2024-01-01 12:00:0{index}", 0, "Benign" if index < 3 else "Malicious")
        for index in range(5)
    ]
    packets = [
        make_tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, base_time),
        make_tcp_packet("10.0.0.9", "10.0.0.10", 9999, 9998, base_time + 1),
    ]
    dataset, _, _, case_dir = create_generic_dataset_case(tmp_path, rows, packets, case_name="ratios")

    assert len(dataset.get_sample_rows_from_combined_csv()) == 5
    assert dataset.get_ts_precision() == Precision.SECOND.value
    assert dataset.caluclate_noise_and_total_packets() == (1, 2)

    noise_path = case_dir / "noise.txt"
    class_path = case_dir / "class.txt"
    dataset.write_noise_ratios_from_combined_pcap_to_file(str(noise_path))
    dataset.write_class_ratios_from_combined_csv_to_file(str(class_path))

    assert "Noise requests: 1" in noise_path.read_text()
    assert "Benign requests: 3" in class_path.read_text()
    assert "Malicious requests: 2" in class_path.read_text()


def test_correct_pcap_pkt_invalid_csv_rows_and_nan_key_helpers(tmp_path):
    valid_row = make_generic_row("10.0.0.1", 1234, "10.0.0.2", 80, "TCP", "2024-01-01 12:00:00", 0, "Benign")
    invalid_row = make_generic_row("10.0.0.1", "", "10.0.0.2", 80, "TCP", "2024-01-01 12:00:01", 0, "Malicious")
    packet = make_tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp())
    dataset, combined_csv, combined_pcap, case_dir = create_generic_dataset_case(
        tmp_path,
        [valid_row, invalid_row],
        [packet],
        case_name="validation_helpers",
    )

    corrected = dataset.correct_pcap_pkt(packet, timedelta(hours=1))
    assert corrected.time == pytest.approx(datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc).timestamp())
    assert dataset.csv_row_contains_invalid_information(valid_row) is False
    assert dataset.csv_row_contains_invalid_information(invalid_row) is True

    none_rows, keys = dataset.get_nan_keys_from_csv(str(combined_csv))
    assert len(none_rows) == 1
    assert len(keys) == 1
    assert get_length_of_pcap(str(combined_pcap)) == 1
    assert csv_row_is_empty([]) is True
    assert csv_row_is_empty(["", "value"]) is False


def test_protocol_duration_and_hour_precision_fallback_paths(tmp_path):
    rows = [
        make_generic_row("10.0.0.1", 1234 + index, "10.0.0.2", 80, "", "2024-01-01 12:00:00", "", "Benign")
        for index in range(5)
    ]
    dataset, _, _, _ = create_generic_dataset_case(
        tmp_path,
        rows,
        [],
        case_name="fallback_paths",
        extra_dataset_kwargs={"protocol_row": None, "flow_duration_row": None},
    )

    assert dataset.get_protocol_from_csv_row(rows[0]) is None
    assert dataset.get_flow_duration_seconds(rows[0]) == 0.0
    assert dataset.get_ts_precision() == Precision.HOUR.value
