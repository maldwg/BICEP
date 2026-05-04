from datetime import datetime, timezone
from pathlib import Path

import pytest

from .helpers import (
    get_selected_plot_datasets,
    get_plot_dataset_name,
    get_plot_original_dir,
    get_plot_output_dir,
    get_plot_sampled_dir,
    get_repo_dataset_data_dir,
    using_external_plot_dirs,
    make_tcp_packet,
    make_udp_packet,
    write_pcap_file,
    write_csv_file,
)
from ..sample_dataset_comparison import (
    build_dataset_from_preset,
    generate_sampling_comparison,
    resolve_csv_pcap_from_dir,
)


def test_repo_dataset_directories_exist(pytestconfig):
    if using_external_plot_dirs(pytestconfig):
        assert get_plot_dataset_name(pytestconfig) is not None
        assert get_plot_original_dir(pytestconfig).exists()
        assert get_plot_sampled_dir(pytestconfig).exists()
        assert get_plot_output_dir(pytestconfig).exists()
        return

    for dataset_name in get_selected_plot_datasets(pytestconfig):
        assert get_repo_dataset_data_dir(dataset_name, pytestconfig=pytestconfig).exists()
        assert get_repo_dataset_data_dir(dataset_name, "original", pytestconfig=pytestconfig).exists()
        assert get_repo_dataset_data_dir(dataset_name, "sampled", pytestconfig=pytestconfig).exists()
        assert get_repo_dataset_data_dir(dataset_name, "plots", pytestconfig=pytestconfig).exists()


def test_external_plot_dirs_require_single_dataset(monkeypatch, tmp_path):
    monkeypatch.setenv("BICEP_PLOT_ORIGINAL_DIR", str(tmp_path / "original"))
    monkeypatch.setenv("BICEP_PLOT_SAMPLED_DIR", str(tmp_path / "sampled"))
    monkeypatch.delenv("BICEP_PLOT_DATASET", raising=False)
    monkeypatch.delenv("BICEP_PLOT_DATASETS", raising=False)

    with pytest.raises(ValueError, match="requires --plot-dataset"):
        get_selected_plot_datasets()


def make_cic_original_rows():
    return [
        ["flow-1", "10.0.0.1", "1234", "10.0.0.2", "80", "6", "2017-07-07 16:30", "1000000", "benign"],
        ["flow-2", "10.0.0.3", "1235", "10.0.0.4", "443", "17", "2017-07-07 16:31", "1500000", "benign"],
        ["flow-3", "10.0.0.5", "1236", "10.0.0.6", "53", "6", "2017-07-07 16:32", "2000000", "malicious"],
        ["flow-4", "10.0.0.7", "1237", "10.0.0.8", "22", "6", "2017-07-07 16:33", "2500000", "malicious"],
        ["flow-5", "10.0.0.9", "1238", "10.0.0.10", "8080", "17", "2017-07-07 16:34", "3000000", "benign"],
        ["flow-6", "10.0.0.11", "1239", "10.0.0.12", "21", "6", "2017-07-07 16:35", "3500000", "malicious"],
    ]


def make_cic_original_packets():
    base_timestamp = datetime(2017, 7, 7, 16, 30, 0, tzinfo=timezone.utc).timestamp()
    packets = []
    for index in range(6):
        src_ip = f"10.0.0.{1 + index * 2}"
        dst_ip = f"10.0.0.{2 + index * 2}"
        src_port = 1234 + index
        dst_port = [80, 443, 53, 22, 8080, 21][index]
        protocol = "udp" if index in (1, 4) else "tcp"
        timestamp = base_timestamp + (index * 60)
        duration = [1, 1.5, 2, 2.5, 3, 3.5][index]
        make_packet = make_udp_packet if protocol == "udp" else make_tcp_packet
        packets.append(make_packet(src_ip, dst_ip, src_port, dst_port, timestamp))
        packets.append(make_packet(src_ip, dst_ip, src_port, dst_port, timestamp + duration / 2))
        packets.append(make_packet(dst_ip, src_ip, dst_port, src_port, timestamp + max(duration - 0.1, 0.01)))
    return packets


def make_ctu_original_rows():
    return [
        ["2011-08-10 10:00:00.000000", "10", "tcp", "10.0.0.1", "1234", "->", "10.0.0.2", "80", "CON", "0", "0", "10", "100", "Benign"],
        ["2011-08-10 10:00:01.000000", "11", "udp", "10.0.0.3", "1235", "->", "10.0.0.4", "53", "CON", "0", "0", "10", "101", "Benign"],
        ["2011-08-10 10:00:02.000000", "12", "tcp", "10.0.0.5", "1236", "->", "10.0.0.6", "443", "CON", "0", "0", "10", "102", "Malicious"],
        ["2011-08-10 10:00:03.000000", "13", "udp", "10.0.0.7", "1237", "->", "10.0.0.8", "161", "CON", "0", "0", "10", "103", "Malicious"],
        ["2011-08-10 10:00:04.000000", "14", "tcp", "10.0.0.9", "1238", "->", "10.0.0.10", "25", "CON", "0", "0", "10", "104", "Benign"],
        ["2011-08-10 10:00:05.000000", "15", "tcp", "10.0.0.11", "1239", "->", "10.0.0.12", "8080", "CON", "0", "0", "10", "105", "Malicious"],
    ]


def make_ctu_original_packets():
    base_timestamp = datetime(2011, 8, 10, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    packets = []
    protocols = ["tcp", "udp", "tcp", "udp", "tcp", "tcp"]
    dst_ports = [80, 53, 443, 161, 25, 8080]
    durations = [10, 11, 12, 13, 14, 15]
    for index in range(6):
        src_ip = f"10.0.0.{1 + index * 2}"
        dst_ip = f"10.0.0.{2 + index * 2}"
        src_port = 1234 + index
        dst_port = dst_ports[index]
        protocol = protocols[index]
        timestamp = base_timestamp + index
        duration = durations[index]
        make_packet = make_udp_packet if protocol == "udp" else make_tcp_packet
        packets.append(make_packet(src_ip, dst_ip, src_port, dst_port, timestamp))
        packets.append(make_packet(src_ip, dst_ip, src_port, dst_port, timestamp + (duration / 2)))
        packets.append(make_packet(dst_ip, src_ip, dst_port, src_port, timestamp + duration - 0.1))
    return packets


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


def make_unsw_original_rows():
    return [
        make_unsw_row("10.0.0.1", 1234, "10.0.0.2", 80, 6, 2, "2024-01-01 11:00:00", "Benign"),
        make_unsw_row("10.0.0.3", 1235, "10.0.0.4", 443, 17, 3, "2024-01-01 11:00:01", "Benign"),
        make_unsw_row("10.0.0.5", 1236, "10.0.0.6", 53, 6, 4, "2024-01-01 11:00:02", "Malicious"),
        make_unsw_row("10.0.0.7", 1237, "10.0.0.8", 22, 6, 5, "2024-01-01 11:00:03", "Malicious"),
        make_unsw_row("10.0.0.9", 1238, "10.0.0.10", 8080, 17, 6, "2024-01-01 11:00:04", "Benign"),
        make_unsw_row("10.0.0.11", 1239, "10.0.0.12", 25, 6, 7, "2024-01-01 11:00:05", "Malicious"),
    ]


def make_unsw_original_packets():
    base_timestamp = datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc).timestamp()
    packets = []
    protocols = ["tcp", "udp", "tcp", "tcp", "udp", "tcp"]
    dst_ports = [80, 443, 53, 22, 8080, 25]
    durations = [2, 3, 4, 5, 6, 7]
    for index in range(6):
        src_ip = f"10.0.0.{1 + index * 2}"
        dst_ip = f"10.0.0.{2 + index * 2}"
        src_port = 1234 + index
        dst_port = dst_ports[index]
        protocol = protocols[index]
        timestamp = base_timestamp + index
        duration = durations[index]
        make_packet = make_udp_packet if protocol == "udp" else make_tcp_packet
        packets.append(make_packet(src_ip, dst_ip, src_port, dst_port, timestamp))
        packets.append(make_packet(src_ip, dst_ip, src_port, dst_port, timestamp + (duration / 2)))
        packets.append(make_packet(dst_ip, src_ip, dst_port, src_port, timestamp + duration - 0.1))
    return packets


DATASET_PERSISTENT_FIXTURES = {
    "cic_ids_2017": {
        "header": ["flow_id", "src_ip", "src_port", "dst_ip", "dst_port", "protocol", "timestamp", "flow_duration", "label"],
        "rows": make_cic_original_rows,
        "packets": make_cic_original_packets,
    },
    "ctu_13": {
        "header": ["StartTime", "Dur", "Proto", "SrcAddr", "Sport", "Dir", "DstAddr", "Dport", "State", "sTos", "dTos", "TotPkts", "TotBytes", "Label"],
        "rows": make_ctu_original_rows,
        "packets": make_ctu_original_packets,
    },
    "unsw_nb15": {
        "header": [f"col_{index}" for index in range(30)],
        "rows": make_unsw_original_rows,
        "packets": make_unsw_original_packets,
    },
}


def write_persistent_sample_inputs(dataset_name, pytestconfig):
    fixture = DATASET_PERSISTENT_FIXTURES[dataset_name]
    original_dir = get_repo_dataset_data_dir(dataset_name, "original", pytestconfig=pytestconfig)
    original_csv = original_dir / "sample.csv"
    original_pcap = original_dir / "sample.pcap"

    if original_csv.exists() and original_pcap.exists():
        return original_csv, original_pcap

    original_rows = fixture["rows"]()
    original_packets = fixture["packets"]()

    write_csv_file(original_csv, fixture["header"], original_rows)
    write_pcap_file(original_pcap, original_packets)
    return original_csv, original_pcap


def assert_plot_bundle_exists(output_dir: Path):
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "label_ratio.png").exists()
    assert (output_dir / "protocol_ratio.png").exists()
    assert (output_dir / "flow_duration_histogram.png").exists()
    assert (output_dir / "timestamp_histogram.png").exists()
    assert (output_dir / "embedding.png").exists()
    assert (output_dir / "packet_count.png").exists()


def count_csv_rows(csv_path):
    with open(csv_path, "r", encoding="utf-8", errors="replace") as csv_file:
        return sum(1 for _ in csv_file) - 1


def run_flow_based_sampling(dataset_name, pytestconfig):
    dataset = build_dataset_from_preset(dataset_name)
    if using_external_plot_dirs(pytestconfig):
        original_dir = get_plot_original_dir(pytestconfig)
        sampled_dir = get_plot_sampled_dir(pytestconfig)
        original_csv, original_pcap = resolve_csv_pcap_from_dir(original_dir, csv_required=True, pcap_required=True, sampled=False)
        existing_sampled_csv, existing_sampled_pcap = resolve_csv_pcap_from_dir(
            sampled_dir,
            csv_required=False,
            pcap_required=False,
            sampled=True,
        )
        if existing_sampled_csv is not None and existing_sampled_pcap is not None:
            dataset.validate_sampled_data(str(existing_sampled_csv), str(existing_sampled_pcap))
            return dataset, original_csv, original_pcap, existing_sampled_csv, existing_sampled_pcap
    else:
        original_csv, original_pcap = write_persistent_sample_inputs(dataset_name, pytestconfig)
        sampled_dir = get_repo_dataset_data_dir(dataset_name, "sampled", pytestconfig=pytestconfig)

    sampled_csv = sampled_dir / "flow_based_sample.csv"
    sampled_pcap = sampled_dir / "flow_based_sample.pcap"

    dataset.combined_csv = str(original_csv)
    dataset.combined_pcap = str(original_pcap)

    for benign_ratio, malicious_ratio in ((0.1, 0.1), (0.25, 0.25), (0.5, 1.0)):
        dataset.sample_from_csv_and_include_pcap_flow_based(
            output_pcap=str(sampled_pcap),
            output_csv=str(sampled_csv),
            sample_ratio_benign=benign_ratio,
            sample_ratio_malicious=malicious_ratio,
        )
        if sampled_csv.exists() and count_csv_rows(sampled_csv) > 0 and sampled_pcap.exists():
            dataset.validate_sampled_data(str(sampled_csv), str(sampled_pcap))
            return dataset, original_csv, original_pcap, sampled_csv, sampled_pcap

    raise AssertionError(f"Sampling did not produce CSV/PCAP output for {dataset_name}")


def test_generate_sampling_comparison_writes_repo_plots_for_each_dataset(pytestconfig):
    for dataset_name in get_selected_plot_datasets(pytestconfig):
        dataset, original_csv, original_pcap, sampled_csv, sampled_pcap = run_flow_based_sampling(dataset_name, pytestconfig)
        output_dir = get_plot_output_dir(pytestconfig, dataset_name=dataset_name)

        report = generate_sampling_comparison(
            dataset,
            original_csv=str(original_csv),
            sampled_csv=str(sampled_csv),
            output_dir=str(output_dir),
            dataset_name=dataset_name,
            original_pcap=str(original_pcap),
            sampled_pcap=str(sampled_pcap),
            embedding_method="pca",
            max_points_per_source=100,
        )

        assert report["original_rows"] > report["sampled_rows"] > 0
        assert report["original_pcap_packets"] > report["sampled_pcap_packets"] > 0
        assert report["embedding_method_used"] == "pca"
        assert all(not protocol_name.isdigit() for protocol_name in report["protocol_ratio_original"])
        assert all(not protocol_name.isdigit() for protocol_name in report["protocol_ratio_sampled"])
        assert_plot_bundle_exists(output_dir)


def test_external_plot_dirs_write_plots_to_current_directory(tmp_path, monkeypatch):
    dataset_name = "cic_ids_2017"
    fixture = DATASET_PERSISTENT_FIXTURES[dataset_name]
    original_dir = tmp_path / "original"
    sampled_dir = tmp_path / "sampled"
    output_dir = tmp_path / "plot-output"
    original_dir.mkdir()
    sampled_dir.mkdir()
    output_dir.mkdir()

    original_csv = original_dir / "sample.csv"
    original_pcap = original_dir / "sample.pcap"
    write_csv_file(original_csv, fixture["header"], fixture["rows"]())
    write_pcap_file(original_pcap, fixture["packets"]())

    monkeypatch.setenv("BICEP_PLOT_DATASET", dataset_name)
    monkeypatch.setenv("BICEP_PLOT_ORIGINAL_DIR", str(original_dir))
    monkeypatch.setenv("BICEP_PLOT_SAMPLED_DIR", str(sampled_dir))
    monkeypatch.delenv("BICEP_PLOT_OUTPUT_DIR", raising=False)
    monkeypatch.chdir(output_dir)

    dataset, resolved_original_csv, resolved_original_pcap, sampled_csv, sampled_pcap = run_flow_based_sampling(
        dataset_name,
        pytestconfig=None,
    )
    resolved_output_dir = get_plot_output_dir(pytestconfig=None, dataset_name=dataset_name)

    report = generate_sampling_comparison(
        dataset,
        original_csv=str(resolved_original_csv),
        sampled_csv=str(sampled_csv),
        output_dir=str(resolved_output_dir),
        dataset_name=dataset_name,
        original_pcap=str(resolved_original_pcap),
        sampled_pcap=str(sampled_pcap),
        embedding_method="pca",
        max_points_per_source=100,
    )

    assert resolved_output_dir == output_dir
    assert sampled_csv.parent == sampled_dir
    assert sampled_pcap.parent == sampled_dir
    assert report["dataset_name"] == dataset_name
    assert report["original_rows"] > report["sampled_rows"] > 0
    assert report["original_pcap_packets"] > report["sampled_pcap_packets"] > 0
    assert_plot_bundle_exists(output_dir)


def test_build_dataset_from_preset_uses_expected_rows():
    dataset = build_dataset_from_preset("ctu_13")
    assert dataset.sip_row == 3
    assert dataset.protocol_row == 2
    assert dataset.flow_duration_unit == "seconds"
