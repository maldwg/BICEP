import csv
import os
from pathlib import Path

from scapy.all import Ether, IP, IPv6, PcapWriter, Raw, TCP, UDP

from ..utils import Dataset, Precision

TEST_DATA_ROOT = Path(__file__).parent / "data"
DATASET_TEST_DIRECTORIES = ("cic_ids_2017", "ctu_13", "unsw_nb15")
DATASET_TEST_SUBDIRECTORIES = ("original", "sampled", "plots")


GENERIC_HEADER = [
    "src_ip",
    "src_port",
    "dst_ip",
    "dst_port",
    "protocol",
    "timestamp",
    "flow_duration",
    "label",
]


def ensure_dataset_data_layout(root):
    root = Path(root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    for dataset_name in DATASET_TEST_DIRECTORIES:
        dataset_dir = root / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        for category_name in DATASET_TEST_SUBDIRECTORIES:
            (dataset_dir / category_name).mkdir(parents=True, exist_ok=True)
    return root


def resolve_test_data_root(pytestconfig=None, root_override=None):
    if root_override is not None:
        return ensure_dataset_data_layout(root_override)

    configured_root = None
    if pytestconfig is not None:
        configured_root = pytestconfig.getoption("--plot-data-root")
    if configured_root is None:
        configured_root = os.getenv("BICEP_PLOT_DATA_ROOT")
    if configured_root is None:
        configured_root = TEST_DATA_ROOT
    return ensure_dataset_data_layout(configured_root)


def get_plot_dataset_name(pytestconfig=None):
    configured_dataset = None
    if pytestconfig is not None:
        configured_dataset = pytestconfig.getoption("--plot-dataset")
    if configured_dataset is None:
        configured_dataset = os.getenv("BICEP_PLOT_DATASET")
    if configured_dataset is None or str(configured_dataset).strip() == "":
        return None

    dataset_name = str(configured_dataset).strip()
    if dataset_name not in DATASET_TEST_DIRECTORIES:
        raise ValueError(f"Unsupported dataset name: {dataset_name}")
    return dataset_name


def get_selected_plot_datasets(pytestconfig=None):
    singular_dataset = get_plot_dataset_name(pytestconfig)
    if singular_dataset is not None:
        return [singular_dataset]

    if using_external_plot_dirs(pytestconfig):
        raise ValueError("External plot directory mode requires --plot-dataset or BICEP_PLOT_DATASET")

    configured_datasets = None
    if pytestconfig is not None:
        configured_datasets = pytestconfig.getoption("--plot-datasets")
    if configured_datasets is None:
        configured_datasets = os.getenv("BICEP_PLOT_DATASETS")

    if configured_datasets is None or str(configured_datasets).strip() == "":
        return list(DATASET_TEST_DIRECTORIES)

    dataset_names = [dataset_name.strip() for dataset_name in str(configured_datasets).split(",") if dataset_name.strip()]
    unsupported = sorted(set(dataset_names) - set(DATASET_TEST_DIRECTORIES))
    if unsupported:
        raise ValueError(f"Unsupported dataset names: {', '.join(unsupported)}")
    return dataset_names


def get_plot_original_dir(pytestconfig=None):
    configured_dir = None
    if pytestconfig is not None:
        configured_dir = pytestconfig.getoption("--plot-original-dir")
    if configured_dir is None:
        configured_dir = os.getenv("BICEP_PLOT_ORIGINAL_DIR")
    if configured_dir is None or str(configured_dir).strip() == "":
        return None
    return Path(str(configured_dir)).expanduser()


def get_plot_sampled_dir(pytestconfig=None):
    configured_dir = None
    if pytestconfig is not None:
        configured_dir = pytestconfig.getoption("--plot-sampled-dir")
    if configured_dir is None:
        configured_dir = os.getenv("BICEP_PLOT_SAMPLED_DIR")
    if configured_dir is None or str(configured_dir).strip() == "":
        return None
    return Path(str(configured_dir)).expanduser()


def using_external_plot_dirs(pytestconfig=None):
    original_dir = get_plot_original_dir(pytestconfig)
    sampled_dir = get_plot_sampled_dir(pytestconfig)
    if (original_dir is None) != (sampled_dir is None):
        raise ValueError("Both plot original and sampled directories must be provided together")
    return original_dir is not None and sampled_dir is not None


def get_plot_output_dir(pytestconfig=None, dataset_name=None):
    configured_dir = None
    if pytestconfig is not None:
        configured_dir = pytestconfig.getoption("--plot-output-dir")
    if configured_dir is None:
        configured_dir = os.getenv("BICEP_PLOT_OUTPUT_DIR")

    if configured_dir is not None and str(configured_dir).strip() != "":
        output_dir = Path(str(configured_dir)).expanduser()
    elif using_external_plot_dirs(pytestconfig):
        output_dir = Path.cwd()
    else:
        if dataset_name is None:
            raise ValueError("dataset_name is required for repo-managed plot directories")
        output_dir = get_repo_dataset_data_dir(dataset_name, "plots", pytestconfig=pytestconfig)

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_repo_dataset_data_dir(dataset_name, category=None, pytestconfig=None, root_override=None):
    if dataset_name not in DATASET_TEST_DIRECTORIES:
        raise ValueError(f"Unsupported dataset name: {dataset_name}")

    dataset_dir = resolve_test_data_root(pytestconfig=pytestconfig, root_override=root_override) / dataset_name
    if category is None:
        return dataset_dir

    if category not in DATASET_TEST_SUBDIRECTORIES:
        raise ValueError(f"Unsupported dataset category: {category}")
    return dataset_dir / category


def write_csv_file(path, header, rows):
    path = Path(path)
    with open(path, "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def write_pcap_file(path, packets):
    path = Path(path)
    with PcapWriter(str(path), append=False, sync=True) as writer:
        for packet in packets:
            writer.write(packet)
    return path


def make_generic_row(src_ip, src_port, dst_ip, dst_port, protocol, timestamp, flow_duration, label):
    return [
        src_ip,
        str(src_port),
        dst_ip,
        str(dst_port),
        str(protocol),
        str(timestamp),
        str(flow_duration),
        str(label),
    ]


def make_tcp_packet(src_ip, dst_ip, src_port, dst_port, timestamp, payload=b"payload"):
    packet = Ether() / IP(src=src_ip, dst=dst_ip) / TCP(sport=src_port, dport=dst_port) / Raw(payload)
    packet.time = timestamp
    return packet


def make_udp_packet(src_ip, dst_ip, src_port, dst_port, timestamp, payload=b"payload"):
    packet = Ether() / IP(src=src_ip, dst=dst_ip) / UDP(sport=src_port, dport=dst_port) / Raw(payload)
    packet.time = timestamp
    return packet


def make_ipv6_udp_packet(src_ip, dst_ip, src_port, dst_port, timestamp, payload=b"payload"):
    packet = Ether() / IPv6(src=src_ip, dst=dst_ip) / UDP(sport=src_port, dport=dst_port) / Raw(payload)
    packet.time = timestamp
    return packet


def create_generic_dataset_case(
    tmp_path,
    rows,
    packets,
    *,
    dataset_cls=Dataset,
    precision=Precision.SECOND.value,
    case_name="case",
    header=None,
    extra_dataset_kwargs=None,
):
    case_dir = Path(tmp_path) / case_name
    case_dir.mkdir(parents=True, exist_ok=True)

    combined_csv = case_dir / "combined.csv"
    combined_pcap = case_dir / "combined.pcap"

    write_csv_file(combined_csv, header or GENERIC_HEADER, rows)
    write_pcap_file(combined_pcap, packets)

    dataset_kwargs = {
        "sip_row": 0,
        "sport_row": 1,
        "dip_row": 2,
        "dport_row": 3,
        "protocol_row": 4,
        "labels_row": 7,
        "ts_row": 5,
        "flow_duration_row": 6,
        "flow_duration_unit": "microseconds",
        "base_dir_path": str(case_dir),
        "labels_path_glob": ["*.csv"],
        "pcap_path_glob": ["*.pcap"],
        "combined_csv": str(combined_csv),
        "combined_pcap": str(combined_pcap),
        "precision": precision,
    }
    if extra_dataset_kwargs:
        dataset_kwargs.update(extra_dataset_kwargs)

    return dataset_cls(**dataset_kwargs), combined_csv, combined_pcap, case_dir
