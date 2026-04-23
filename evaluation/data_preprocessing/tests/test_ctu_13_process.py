import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from scapy.all import rdpcap

from .helpers import write_csv_file, write_pcap_file, make_tcp_packet
from ..ctu_13.process import CTU
from ..utils import Precision


def build_ctu_dataset(tmp_path):
    base_dir = tmp_path / "ctu"
    scenario_dir = base_dir / "scenario_1"
    scenario_dir.mkdir(parents=True, exist_ok=True)

    combined_csv = base_dir / "combined.csv"
    combined_pcap = base_dir / "combined.pcap"

    dataset = CTU(
        sip_row=3,
        sport_row=4,
        dip_row=6,
        dport_row=7,
        protocol_row=2,
        labels_row=-1,
        ts_row=0,
        flow_duration_row=1,
        flow_duration_unit="seconds",
        base_dir_path=str(base_dir),
        labels_path_glob=["*/*.binetflow"],
        pcap_path_glob=["*/*.pcap"],
        combined_csv=str(combined_csv),
        combined_pcap=str(combined_pcap),
        precision=Precision.SECOND.value,
    )
    return dataset, scenario_dir, combined_csv, combined_pcap


def assert_plot_bundle_exists(output_dir: Path):
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "label_ratio.png").exists()
    assert (output_dir / "protocol_ratio.png").exists()
    assert (output_dir / "flow_duration_histogram.png").exists()
    assert (output_dir / "timestamp_histogram.png").exists()
    assert (output_dir / "embedding.png").exists()
    assert (output_dir / "packet_count.png").exists()


def test_ctu_correct_csv_row_maps_labels_and_shifts_time(tmp_path):
    dataset, _, _, _ = build_ctu_dataset(tmp_path)
    row = ["2011-08-10 12:00:00.000000", "12.5", "tcp", "10.0.0.1", "1234", "->", "10.0.0.2", "80", "CON", "0", "0", "10", "100", "Background"]

    corrected = dataset.correct_csv_row(row.copy())

    assert corrected[0] == "2011-08-10 10:00:00.000000"
    assert corrected[-1] == "Benign"


def test_ctu_convert_binetflow_to_csv_and_combine_merges_files(tmp_path):
    dataset, scenario_dir, combined_csv, _ = build_ctu_dataset(tmp_path)
    header = ["StartTime", "Dur", "Proto", "SrcAddr", "Sport", "Dir", "DstAddr", "Dport", "State", "sTos", "dTos", "TotPkts", "TotBytes", "Label"]
    benign_row = ["2011-08-10 12:00:00.000000", "10", "tcp", "10.0.0.1", "1234", "->", "10.0.0.2", "80", "CON", "0", "0", "10", "100", "Background"]
    malicious_row = ["2011-08-10 12:00:01.000000", "5", "udp", "10.0.0.3", "4000", "->", "10.0.0.4", "53", "CON", "0", "0", "10", "100", "Botnet"]
    invalid_row = ["2011-08-10 12:00:02.000000", "5", "udp", "bad-ip", "4000", "->", "10.0.0.4", "53", "CON", "0", "0", "10", "100", "Botnet"]

    write_csv_file(scenario_dir / "a.binetflow", header, [benign_row, invalid_row])
    write_csv_file(scenario_dir / "b.binetflow", header, [malicious_row])

    dataset.labels_files = [str(scenario_dir / "a.binetflow"), str(scenario_dir / "b.binetflow")]
    dataset.convert_binetflow_to_csv_and_combine()

    with open(combined_csv, newline="") as csv_file:
        rows = list(csv.reader(csv_file))

    assert len(rows) == 3
    assert rows[1][-1] == "Benign"
    assert rows[2][-1] == "Malicious"


def test_ctu_combine_pcaps_and_correct_pcap_pkt(tmp_path):
    dataset, scenario_dir, _, combined_pcap = build_ctu_dataset(tmp_path)
    timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    packet = make_tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, timestamp)
    write_pcap_file(scenario_dir / "one.pcap", [packet])
    write_pcap_file(scenario_dir / "two.pcap", [make_tcp_packet("10.0.0.3", "10.0.0.4", 4321, 443, timestamp + 1)])

    corrected = dataset.correct_pcap_pkt(packet.copy())
    assert corrected.time == pytest.approx((datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)).timestamp())

    dataset.pcap_files = [str(scenario_dir / "one.pcap"), str(scenario_dir / "two.pcap")]
    dataset.combine_pcaps()
    assert len(rdpcap(str(combined_pcap))) == 2


def test_ctu_sampling_helpers_write_aligned_outputs(tmp_path):
    dataset, _, combined_csv, combined_pcap = build_ctu_dataset(tmp_path)
    header = ["StartTime", "Dur", "Proto", "SrcAddr", "Sport", "Dir", "DstAddr", "Dport", "State", "sTos", "dTos", "TotPkts", "TotBytes", "Label"]
    rows = [
        ["2011-08-10 12:00:00.000000", "20", "tcp", "10.0.0.1", "1234", "->", "10.0.0.2", "80", "CON", "0", "0", "10", "100", "Botnet"],
        ["2011-08-10 12:00:01.000000", "20", "tcp", "10.0.0.3", "1235", "->", "10.0.0.4", "80", "CON", "0", "0", "10", "100", "Botnet"],
        ["2011-08-10 12:00:02.000000", "20", "tcp", "10.0.0.5", "1236", "->", "10.0.0.6", "80", "CON", "0", "0", "10", "100", "Normal"],
        ["2011-08-10 12:00:03.000000", "20", "tcp", "10.0.0.7", "1237", "->", "10.0.0.8", "80", "CON", "0", "0", "10", "100", "Normal"],
        ["2011-08-10 12:00:04.000000", "20", "tcp", "10.0.0.9", "1238", "->", "10.0.0.10", "80", "CON", "0", "0", "10", "100", "Normal"],
    ]
    corrected_rows = [dataset.correct_csv_row(row.copy()) for row in rows]
    write_csv_file(combined_csv, header, corrected_rows)

    base_time = datetime(2011, 8, 10, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    packets = [
        make_tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, base_time),
        make_tcp_packet("10.0.0.5", "10.0.0.6", 1236, 80, base_time + 2),
        make_tcp_packet("10.0.0.7", "10.0.0.8", 1237, 80, base_time + 3),
    ]
    write_pcap_file(combined_pcap, packets)

    csv_records, sampled_rows = dataset.sample_from_csv_with_target_malicious_and_random_benign(
        str(combined_csv),
        target_benign=2,
        target_malicious=1,
        packet_buffer=1,
    )
    assert len(csv_records) == 3
    assert len(sampled_rows) == 4

    output_csv = combined_csv.parent / "sampled.csv"
    output_pcap = combined_pcap.parent / "sampled.pcap"
    dataset.sample_ctu_special_from_combined_csv_first(
        str(output_csv),
        str(output_pcap),
        malicious_ratio=0.5,
        benign_factor=2,
        packet_buffer=1,
    )

    with open(output_csv, newline="") as csv_file:
        output_rows = list(csv.reader(csv_file))
    assert len(output_rows) >= 2
    assert len(rdpcap(str(output_pcap))) > 0


def test_ctu_plot_sampled_dataset_comparison_writes_plot_bundle(tmp_path):
    dataset, _, _, _ = build_ctu_dataset(tmp_path)
    header = ["StartTime", "Dur", "Proto", "SrcAddr", "Sport", "Dir", "DstAddr", "Dport", "State", "sTos", "dTos", "TotPkts", "TotBytes", "Label"]
    original_rows = [
        ["2011-08-10 10:00:00.000000", "10", "tcp", "10.0.0.1", "1234", "->", "10.0.0.2", "80", "CON", "0", "0", "10", "100", "Benign"],
        ["2011-08-10 10:00:01.000000", "15", "udp", "10.0.0.3", "1235", "->", "10.0.0.4", "53", "CON", "0", "0", "10", "120", "Malicious"],
    ]
    sampled_rows = [original_rows[0]]

    original_csv = tmp_path / "original.csv"
    sampled_csv = tmp_path / "sampled.csv"
    original_pcap = tmp_path / "original.pcap"
    sampled_pcap = tmp_path / "sampled.pcap"
    output_dir = tmp_path / "plots"

    write_csv_file(original_csv, header, original_rows)
    write_csv_file(sampled_csv, header, sampled_rows)

    base_timestamp = datetime(2011, 8, 10, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    write_pcap_file(
        original_pcap,
        [
            make_tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, base_timestamp),
            make_tcp_packet("10.0.0.3", "10.0.0.4", 1235, 53, base_timestamp + 1),
        ],
    )
    write_pcap_file(
        sampled_pcap,
        [make_tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, base_timestamp)],
    )

    report = dataset.plot_sampled_dataset_comparison(
        original_csv=str(original_csv),
        sampled_csv=str(sampled_csv),
        original_pcap=str(original_pcap),
        sampled_pcap=str(sampled_pcap),
        output_dir=str(output_dir),
        embedding_method="pca",
        max_points_per_source=100,
    )

    assert report["dataset_name"] == "ctu_13"
    assert report["original_rows"] == 2
    assert report["sampled_rows"] == 1
    assert_plot_bundle_exists(output_dir)
