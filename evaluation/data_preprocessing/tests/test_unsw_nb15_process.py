import csv
from datetime import datetime, timezone
from pathlib import Path

from scapy.all import CookedLinux, IP, UDP, rdpcap

from .helpers import write_csv_file, write_pcap_file, make_tcp_packet
from ..unsw_nb15.process import UNSBW
from ..utils import Precision


def build_unsw_dataset(tmp_path):
    base_dir = tmp_path / "unsw"
    labels_dir = base_dir / "labels"
    pcaps_dir_1 = base_dir / "pcaps" / "1"
    pcaps_dir_2 = base_dir / "pcaps" / "2"
    labels_dir.mkdir(parents=True, exist_ok=True)
    pcaps_dir_1.mkdir(parents=True, exist_ok=True)
    pcaps_dir_2.mkdir(parents=True, exist_ok=True)

    combined_csv = base_dir / "combined.csv"
    combined_pcap = base_dir / "combined.pcap"

    dataset = UNSBW(
        sip_row=0,
        sport_row=1,
        dip_row=2,
        dport_row=3,
        protocol_row=4,
        labels_row=-1,
        ts_row=28,
        flow_duration_row=6,
        flow_duration_unit="seconds",
        base_dir_path=str(base_dir),
        labels_path_glob=[
            "labels/UNSW-NB15_1.csv",
            "labels/UNSW-NB15_2.csv",
            "labels/UNSW-NB15_3.csv",
            "labels/UNSW-NB15_4.csv",
        ],
        pcap_path_glob=["pcaps/1/*.pcap", "pcaps/2/*.pcap"],
        combined_csv=str(combined_csv),
        combined_pcap=str(combined_pcap),
        precision=Precision.SECOND.value,
    )
    return dataset, labels_dir, pcaps_dir_1, pcaps_dir_2, combined_csv, combined_pcap


def assert_plot_bundle_exists(output_dir: Path):
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "label_ratio.png").exists()
    assert (output_dir / "protocol_ratio.png").exists()
    assert (output_dir / "flow_duration_histogram.png").exists()
    assert (output_dir / "timestamp_histogram.png").exists()
    assert (output_dir / "embedding.png").exists()
    assert (output_dir / "packet_count.png").exists()


def make_unsw_row(src_ip, src_port, dst_ip, dst_port, proto, duration, timestamp, label, total_columns=30):
    row = ["0"] * total_columns
    row[0] = src_ip
    row[1] = str(src_port)
    row[2] = dst_ip
    row[3] = str(dst_port)
    row[4] = str(proto)
    row[6] = str(duration)
    row[28] = str(timestamp)
    row[-1] = str(label)
    return row


def test_unsw_correct_csv_row_and_sll_to_ether(tmp_path):
    dataset, _, _, _, _, _ = build_unsw_dataset(tmp_path)
    row = make_unsw_row("10.0.0.1", 1234, "10.0.0.2", 80, 6, 2, 1_704_110_400, 1)

    corrected = dataset.correct_csv_row(row.copy())
    assert corrected[-1] == "Malicious"
    assert corrected[28] == "2024-01-01 11:00:00"

    cooked_packet = CookedLinux() / IP(src="10.0.0.1", dst="10.0.0.2") / UDP(sport=1234, dport=53)
    ether_packet = dataset.sll_to_ether(cooked_packet)
    assert ether_packet.haslayer("Ether")
    assert ether_packet.haslayer(IP)


def test_unsw_combine_csvs_builds_header_and_combines_rows(tmp_path):
    dataset, labels_dir, _, _, combined_csv, _ = build_unsw_dataset(tmp_path)
    feature_header = ["id", "name"]
    feature_rows = [[str(index), f"f{index}"] for index in range(30)]
    write_csv_file(labels_dir / "NUSW-NB15_features.csv", feature_header, feature_rows)

    data_row_1 = make_unsw_row("10.0.0.1", 1234, "10.0.0.2", 80, 6, 2, 1_704_110_400, 0)
    data_row_2 = make_unsw_row("10.0.0.3", 4321, "10.0.0.4", 53, 17, 3, 1_704_110_401, 1)
    with open(labels_dir / "UNSW-NB15_1.csv", "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(data_row_1)
    with open(labels_dir / "UNSW-NB15_2.csv", "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(data_row_2)

    dataset.labels_files = [str(labels_dir / "UNSW-NB15_1.csv"), str(labels_dir / "UNSW-NB15_2.csv")]
    dataset.combine_csvs()

    with open(combined_csv, newline="") as csv_file:
        rows = list(csv.reader(csv_file))

    assert rows[0][0] == "f0"
    assert len(rows) == 3
    assert rows[1][-1] == "Benign"
    assert rows[2][-1] == "Malicious"


def test_unsw_combine_pcaps_converts_packets(tmp_path):
    dataset, _, pcaps_dir_1, pcaps_dir_2, _, combined_pcap = build_unsw_dataset(tmp_path)
    timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    cooked_packet = CookedLinux() / IP(src="10.0.0.1", dst="10.0.0.2") / UDP(sport=1234, dport=53)
    cooked_packet.time = timestamp
    write_pcap_file(pcaps_dir_1 / "one.pcap", [cooked_packet])
    write_pcap_file(pcaps_dir_2 / "two.pcap", [make_tcp_packet("10.0.0.3", "10.0.0.4", 4321, 443, timestamp + 1)])

    dataset.pcap_files = [str(pcaps_dir_1 / "one.pcap"), str(pcaps_dir_2 / "two.pcap")]
    dataset.combine_pcaps()

    packets = rdpcap(str(combined_pcap))
    assert len(packets) == 2
    assert packets[0].haslayer("Ether")


def test_unsw_plot_sampled_dataset_comparison_writes_plot_bundle(tmp_path):
    dataset, _, _, _, _, _ = build_unsw_dataset(tmp_path)
    header = [f"col_{index}" for index in range(30)]
    original_rows = [
        make_unsw_row("10.0.0.1", 1234, "10.0.0.2", 80, 6, 2, "2024-01-01 11:00:00", "Benign"),
        make_unsw_row("10.0.0.3", 4321, "10.0.0.4", 53, 17, 3, "2024-01-01 11:00:01", "Malicious"),
    ]
    sampled_rows = [original_rows[0]]

    original_csv = tmp_path / "original.csv"
    sampled_csv = tmp_path / "sampled.csv"
    original_pcap = tmp_path / "original.pcap"
    sampled_pcap = tmp_path / "sampled.pcap"
    output_dir = tmp_path / "plots"

    write_csv_file(original_csv, header, original_rows)
    write_csv_file(sampled_csv, header, sampled_rows)

    base_timestamp = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc).timestamp()
    write_pcap_file(
        original_pcap,
        [
            make_tcp_packet("10.0.0.1", "10.0.0.2", 1234, 80, base_timestamp),
            make_tcp_packet("10.0.0.3", "10.0.0.4", 4321, 53, base_timestamp + 1),
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

    assert report["dataset_name"] == "unsw_nb15"
    assert report["original_rows"] == 2
    assert report["sampled_rows"] == 1
    assert_plot_bundle_exists(output_dir)
