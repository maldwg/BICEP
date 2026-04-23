import csv
from datetime import datetime, timezone
from pathlib import Path

from scapy.all import rdpcap

from .helpers import write_csv_file, write_pcap_file, make_tcp_packet
from ..cic_ids_2017.process import CICIDS
from ..utils import Precision


def build_cic_dataset(tmp_path):
    base_dir = tmp_path / "cic"
    label_dir = base_dir / "labels"
    pcap_dir = base_dir / "pcaps"
    label_dir.mkdir(parents=True, exist_ok=True)
    pcap_dir.mkdir(parents=True, exist_ok=True)

    combined_csv = base_dir / "combined.csv"
    combined_pcap = base_dir / "combined.pcap"

    dataset = CICIDS(
        sip_row=1,
        sport_row=2,
        dip_row=3,
        dport_row=4,
        protocol_row=5,
        labels_row=-1,
        ts_row=6,
        flow_duration_row=7,
        flow_duration_unit="microseconds",
        base_dir_path=str(base_dir),
        labels_path_glob=["labels/*.csv"],
        pcap_path_glob=["pcaps/*.pcap"],
        combined_csv=str(combined_csv),
        combined_pcap=str(combined_pcap),
        precision=Precision.MINUTE.value,
    )
    return dataset, label_dir, pcap_dir, combined_csv, combined_pcap


def assert_plot_bundle_exists(output_dir: Path):
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "label_ratio.png").exists()
    assert (output_dir / "protocol_ratio.png").exists()
    assert (output_dir / "flow_duration_histogram.png").exists()
    assert (output_dir / "timestamp_histogram.png").exists()
    assert (output_dir / "embedding.png").exists()
    assert (output_dir / "packet_count.png").exists()


def test_cic_correct_csv_row_normalizes_time_and_label(tmp_path):
    dataset, _, _, _, _ = build_cic_dataset(tmp_path)
    row = ["id", "10.0.0.1", "1234", "10.0.0.2", "80", "6", "07/07/2017 01:30", "60000000", "DoS Hulk"]

    corrected = dataset.correct_csv_row(row.copy())

    assert corrected[6] == "2017-07-07 16:30"
    assert corrected[-1] == "malicious"


def test_cic_combine_csv_merges_headers_and_filters_invalid_rows(tmp_path):
    dataset, label_dir, _, combined_csv, _ = build_cic_dataset(tmp_path)
    header = ["Flow ID", " Source IP", " Source Port", " Destination IP", " Destination Port", " Protocol", " Timestamp", " Flow Duration", " Label"]
    valid_row = ["id-1", "10.0.0.1", "1234", "10.0.0.2", "80", "6", "07/07/2017 08:59", "1000000", "BENIGN"]
    invalid_row = ["id-2", "invalid-ip", "1234", "10.0.0.2", "80", "6", "07/07/2017 08:59", "1000000", "BENIGN"]
    malicious_row = ["id-3", "10.0.0.3", "4321", "10.0.0.4", "443", "6", "07/07/2017 09:01", "2000000", "DoS Hulk"]

    write_csv_file(label_dir / "a.csv", header, [valid_row, invalid_row])
    write_csv_file(label_dir / "b.csv", header, [malicious_row])

    dataset.labels_files = [str(label_dir / "a.csv"), str(label_dir / "b.csv")]
    dataset.combine_csv()

    with open(combined_csv, newline="") as csv_file:
        rows = list(csv.reader(csv_file))

    assert rows[0] == header
    assert len(rows) == 3
    assert rows[1][-1] == "benign"
    assert rows[2][-1] == "malicious"


def test_cic_combine_pcaps_appends_packets(tmp_path):
    dataset, _, pcap_dir, _, combined_pcap = build_cic_dataset(tmp_path)
    timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    write_pcap_file(pcap_dir / "one.pcap", [make_tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, timestamp)])
    write_pcap_file(pcap_dir / "two.pcap", [make_tcp_packet("10.0.0.3", "10.0.0.4", 4321, 443, timestamp + 1)])

    dataset.pcap_files = [str(pcap_dir / "one.pcap"), str(pcap_dir / "two.pcap")]
    dataset.combine_pcaps()

    assert len(rdpcap(str(combined_pcap))) == 2


def test_cic_plot_sampled_dataset_comparison_writes_plot_bundle(tmp_path):
    dataset, _, _, _, _ = build_cic_dataset(tmp_path)
    header = ["Flow ID", " Source IP", " Source Port", " Destination IP", " Destination Port", " Protocol", " Timestamp", " Flow Duration", " Label"]
    original_rows = [
        ["id-1", "10.0.0.1", "1234", "10.0.0.2", "80", "6", "2017-07-07 16:30", "1000000", "benign"],
        ["id-2", "10.0.0.3", "4321", "10.0.0.4", "443", "17", "2017-07-07 16:31", "2000000", "malicious"],
    ]
    sampled_rows = [original_rows[0]]

    original_csv = tmp_path / "original.csv"
    sampled_csv = tmp_path / "sampled.csv"
    original_pcap = tmp_path / "original.pcap"
    sampled_pcap = tmp_path / "sampled.pcap"
    output_dir = tmp_path / "plots"

    write_csv_file(original_csv, header, original_rows)
    write_csv_file(sampled_csv, header, sampled_rows)

    base_timestamp = datetime(2017, 7, 7, 16, 30, 0, tzinfo=timezone.utc).timestamp()
    write_pcap_file(
        original_pcap,
        [
            make_tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, base_timestamp),
            make_tcp_packet("10.0.0.3", "10.0.0.4", 4321, 443, base_timestamp + 60),
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

    assert report["dataset_name"] == "cic_ids_2017"
    assert report["original_rows"] == 2
    assert report["sampled_rows"] == 1
    assert_plot_bundle_exists(output_dir)
