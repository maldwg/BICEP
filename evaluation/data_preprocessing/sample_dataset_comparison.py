import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-data-preprocessing")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/scapy-cache")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scapy.data import IP_PROTOS
from scapy.utils import RawPcapReader

try:
    from sklearn.manifold import TSNE
except ImportError:  # pragma: no cover - covered through fallback behavior
    TSNE = None

try:
    from .utils import Dataset, Precision, normalize_protocol_value
except ImportError:  # pragma: no cover - supports direct script execution
    from data_preprocessing.utils import Dataset, Precision, normalize_protocol_value


DATASET_PRESETS = {
    "cic_ids_2017": {
        "sip_row": 1,
        "sport_row": 2,
        "dip_row": 3,
        "dport_row": 4,
        "protocol_row": 5,
        "labels_row": -1,
        "ts_row": 6,
        "flow_duration_row": 7,
        "flow_duration_unit": "microseconds",
        "precision": Precision.MINUTE.value,
    },
    "ctu_13": {
        "sip_row": 3,
        "sport_row": 4,
        "dip_row": 6,
        "dport_row": 7,
        "protocol_row": 2,
        "labels_row": -1,
        "ts_row": 0,
        "flow_duration_row": 1,
        "flow_duration_unit": "seconds",
        "precision": Precision.SECOND.value,
    },
    "unsw_nb15": {
        "sip_row": 0,
        "sport_row": 1,
        "dip_row": 2,
        "dport_row": 3,
        "protocol_row": 4,
        "labels_row": -1,
        "ts_row": 28,
        "flow_duration_row": 6,
        "flow_duration_unit": "seconds",
        "precision": Precision.SECOND.value,
    },
}

EMBEDDING_FEATURE_COLUMNS = [
    "src_port",
    "dst_port",
    "protocol",
    "src_ip_hash",
    "dst_ip_hash",
    "timestamp_epoch",
    "flow_duration_seconds",
]


def build_dataset_from_preset(dataset_name):
    if dataset_name not in DATASET_PRESETS:
        raise ValueError(f"Unknown dataset preset: {dataset_name}")

    return Dataset(
        base_dir_path=".",
        labels_path_glob=[],
        pcap_path_glob=[],
        combined_csv="",
        combined_pcap="",
        **DATASET_PRESETS[dataset_name],
    )


def stable_numeric_id(value):
    return int.from_bytes(hashlib.sha1(str(value).encode("utf-8")).digest()[:8], "big")


def parse_timestamp_to_epoch(dataset, value):
    parsed = dataset.parse_csv_timestamp_value(value)
    return (parsed - datetime(1970, 1, 1)).total_seconds()


def load_csv_frame(csv_path):
    return pd.read_csv(csv_path, low_memory=False)


def find_first_matching_file(directory, preferred_names, patterns):
    directory = Path(directory).expanduser()
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    for file_name in preferred_names:
        candidate = directory / file_name
        if candidate.exists():
            return candidate

    matches = []
    for pattern in patterns:
        matches.extend(sorted(path for path in directory.glob(pattern) if path.is_file()))

    if matches:
        return matches[0]
    return None


def resolve_csv_pcap_from_dir(directory, *, csv_required=True, pcap_required=False, sampled=False):
    csv_preferences = ["flow_based_sample.csv", "sampled.csv", "sample.csv"] if sampled else ["sample.csv", "combined.csv"]
    pcap_preferences = ["flow_based_sample.pcap", "sampled.pcap", "sample.pcap"] if sampled else ["sample.pcap", "combined.pcap"]

    csv_path = find_first_matching_file(directory, csv_preferences, ("*.csv",))
    pcap_path = find_first_matching_file(directory, pcap_preferences, ("*.pcap", "*.pcapng"))

    if csv_required and csv_path is None:
        raise FileNotFoundError(f"No CSV file found in directory: {directory}")
    if pcap_required and pcap_path is None:
        raise FileNotFoundError(f"No PCAP file found in directory: {directory}")

    return csv_path, pcap_path


def normalize_labels(label_series):
    return label_series.fillna("unknown").astype(str).str.strip().str.lower()


def normalize_protocols(protocol_series):
    def normalize(value):
        if pd.isna(value):
            return "unknown"
        normalized = normalize_protocol_value(value)
        if normalized in (None, ""):
            return "unknown"
        return normalized

    return protocol_series.map(normalize)


def protocol_display_name(value):
    if value in ("unknown", "", None):
        return "UNKNOWN"

    try:
        protocol_number = int(float(value))
    except (TypeError, ValueError):
        return str(value).strip().upper()

    try:
        return str(IP_PROTOS[protocol_number]).upper()
    except Exception:
        return f"PROTO {protocol_number}"


def prepare_feature_frame(dataset, csv_frame, source_name):
    prepared = pd.DataFrame(index=csv_frame.index)
    prepared["source"] = source_name
    prepared["label"] = normalize_labels(csv_frame.iloc[:, dataset.labels_row])
    prepared["protocol_name"] = normalize_protocols(
        csv_frame.iloc[:, dataset.protocol_row] if dataset.protocol_row is not None else pd.Series(index=csv_frame.index, dtype=object)
    )
    prepared["protocol_display"] = prepared["protocol_name"].map(protocol_display_name)

    def protocol_to_numeric(value):
        if value in ("unknown", "", None):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(stable_numeric_id(value) % 10000)

    prepared["protocol"] = prepared["protocol_name"].map(protocol_to_numeric)
    prepared["src_port"] = pd.to_numeric(csv_frame.iloc[:, dataset.sport_row], errors="coerce").fillna(0.0)
    prepared["dst_port"] = pd.to_numeric(csv_frame.iloc[:, dataset.dport_row], errors="coerce").fillna(0.0)
    prepared["src_ip_hash"] = csv_frame.iloc[:, dataset.sip_row].map(stable_numeric_id).astype(float)
    prepared["dst_ip_hash"] = csv_frame.iloc[:, dataset.dip_row].map(stable_numeric_id).astype(float)
    prepared["timestamp_epoch"] = csv_frame.iloc[:, dataset.ts_row].map(lambda value: parse_timestamp_to_epoch(dataset, value))
    prepared["flow_duration_seconds"] = csv_frame.apply(
        lambda row: dataset.get_flow_duration_seconds(row.tolist()),
        axis=1,
    )
    return prepared


def sample_embedding_frame(comparison_frame, max_points_per_source, random_state):
    sampled_frames = []
    for source_name, source_frame in comparison_frame.groupby("source"):
        if len(source_frame) > max_points_per_source:
            sampled_frames.append(source_frame.sample(n=max_points_per_source, random_state=random_state))
        else:
            sampled_frames.append(source_frame)
    if not sampled_frames:
        return comparison_frame.iloc[0:0].copy()
    return pd.concat(sampled_frames, ignore_index=True)


def standardize_features(feature_values):
    centered = feature_values - feature_values.mean(axis=0, keepdims=True)
    scales = centered.std(axis=0, keepdims=True)
    scales[scales == 0] = 1.0
    return centered / scales


def compute_pca_embedding(feature_values):
    if len(feature_values) == 0:
        return np.empty((0, 2))
    standardized = standardize_features(feature_values)
    if standardized.shape[1] == 1:
        return np.column_stack([standardized[:, 0], np.zeros(len(standardized))])
    _, _, right_vectors = np.linalg.svd(standardized, full_matrices=False)
    components = right_vectors[:2].T
    embedding = standardized @ components
    if embedding.shape[1] == 1:
        embedding = np.column_stack([embedding[:, 0], np.zeros(len(embedding))])
    return embedding[:, :2]


def compute_embedding(comparison_frame, embedding_method="auto", random_state=42):
    feature_values = comparison_frame[EMBEDDING_FEATURE_COLUMNS].fillna(0.0).to_numpy(dtype=float)
    if len(feature_values) == 0:
        return np.empty((0, 2)), "none"

    if embedding_method not in {"auto", "tsne", "pca"}:
        raise ValueError(f"Unsupported embedding method: {embedding_method}")

    use_tsne = embedding_method == "tsne" or (embedding_method == "auto" and TSNE is not None)
    if use_tsne and TSNE is not None and len(feature_values) >= 4:
        standardized = standardize_features(feature_values)
        perplexity = max(2, min(30, len(standardized) // 3))
        perplexity = min(perplexity, len(standardized) - 1)
        embedding = TSNE(
            n_components=2,
            init="pca",
            learning_rate="auto",
            perplexity=perplexity,
            random_state=random_state,
        ).fit_transform(standardized)
        return embedding, "tsne"

    return compute_pca_embedding(feature_values), "pca"


def ratio_dict(series):
    counts = series.value_counts(normalize=True).sort_index()
    return {str(key): float(value) for key, value in counts.items()}


def summary_stats(series):
    if len(series) == 0:
        return {}
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) == 0:
        return {}
    return {
        "min": float(clean.min()),
        "p25": float(clean.quantile(0.25)),
        "median": float(clean.quantile(0.5)),
        "p75": float(clean.quantile(0.75)),
        "max": float(clean.max()),
        "mean": float(clean.mean()),
    }


def ratio_delta(original_ratios, sampled_ratios):
    keys = sorted(set(original_ratios) | set(sampled_ratios))
    return {
        key: float(abs(original_ratios.get(key, 0.0) - sampled_ratios.get(key, 0.0)))
        for key in keys
    }


def build_report(dataset_name, original_frame, sampled_frame, embedding_method_used):
    original_label_ratio = ratio_dict(original_frame["label"])
    sampled_label_ratio = ratio_dict(sampled_frame["label"])
    original_protocol_ratio = ratio_dict(original_frame["protocol_display"])
    sampled_protocol_ratio = ratio_dict(sampled_frame["protocol_display"])

    return {
        "dataset_name": dataset_name,
        "embedding_method_used": embedding_method_used,
        "original_rows": int(len(original_frame)),
        "sampled_rows": int(len(sampled_frame)),
        "label_ratio_original": original_label_ratio,
        "label_ratio_sampled": sampled_label_ratio,
        "label_ratio_delta": ratio_delta(original_label_ratio, sampled_label_ratio),
        "protocol_ratio_original": original_protocol_ratio,
        "protocol_ratio_sampled": sampled_protocol_ratio,
        "protocol_ratio_delta": ratio_delta(original_protocol_ratio, sampled_protocol_ratio),
        "original_flow_duration_seconds": summary_stats(original_frame["flow_duration_seconds"]),
        "sampled_flow_duration_seconds": summary_stats(sampled_frame["flow_duration_seconds"]),
        "original_timestamp_epoch": summary_stats(original_frame["timestamp_epoch"]),
        "sampled_timestamp_epoch": summary_stats(sampled_frame["timestamp_epoch"]),
    }


def save_report(report, output_dir):
    report_path = Path(output_dir) / "summary.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True))
    return report_path


def count_pcap_packets(pcap_path):
    packet_count = 0
    with RawPcapReader(str(pcap_path)) as reader:
        for _packet_data, _metadata in reader:
            packet_count += 1
    return packet_count


def plot_packet_count_comparison(original_packets, sampled_packets, output_path):
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(["original", "sampled"], [original_packets, sampled_packets], color=["#1f77b4", "#ff7f0e"])
    ax.set_title("PCAP Packet Counts")
    ax.set_ylabel("Packets")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_ratio_comparison(original_frame, sampled_frame, column_name, output_path, title):
    comparison = pd.concat(
        [
            original_frame[column_name].value_counts(normalize=True).rename("original"),
            sampled_frame[column_name].value_counts(normalize=True).rename("sampled"),
        ],
        axis=1,
    ).fillna(0.0)
    comparison = comparison.sort_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    comparison.plot(kind="bar", ax=ax, color=["#1f77b4", "#ff7f0e"])
    ax.set_ylabel("Ratio")
    ax.set_xlabel(column_name.replace("_", " ").title())
    ax.set_title(title)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_histogram_comparison(original_frame, sampled_frame, column_name, output_path, title, x_label):
    original_values = pd.to_numeric(original_frame[column_name], errors="coerce").dropna()
    sampled_values = pd.to_numeric(sampled_frame[column_name], errors="coerce").dropna()

    fig, ax = plt.subplots(figsize=(8, 5))
    bins = max(10, min(40, int(np.sqrt(max(len(original_values), len(sampled_values), 1))) * 2))
    ax.hist(original_values, bins=bins, alpha=0.55, density=True, label="original", color="#1f77b4")
    ax.hist(sampled_values, bins=bins, alpha=0.55, density=True, label="sampled", color="#ff7f0e")
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel("Density")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_embedding(comparison_frame, embedding, output_path, embedding_method_used):
    if len(comparison_frame) == 0:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.set_title("No rows available for embedding")
        fig.tight_layout()
        fig.savefig(output_path)
        plt.close(fig)
        return

    embedded_frame = comparison_frame.copy()
    embedded_frame["x"] = embedding[:, 0]
    embedded_frame["y"] = embedding[:, 1]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    source_colors = {"original": "#1f77b4", "sampled": "#ff7f0e"}
    for source_name, source_frame in embedded_frame.groupby("source"):
        axes[0].scatter(
            source_frame["x"],
            source_frame["y"],
            s=22,
            alpha=0.7,
            label=source_name,
            color=source_colors.get(source_name, "#777777"),
        )
    axes[0].set_title(f"{embedding_method_used.upper()} Overlay By Source")
    axes[0].legend(loc="best")

    label_palette = {
        "benign": "#2ca02c",
        "malicious": "#d62728",
    }
    for label_name, label_frame in embedded_frame.groupby("label"):
        axes[1].scatter(
            label_frame["x"],
            label_frame["y"],
            s=22,
            alpha=0.7,
            label=label_name,
            color=label_palette.get(label_name, "#9467bd"),
        )
    axes[1].set_title(f"{embedding_method_used.upper()} Overlay By Label")
    axes[1].legend(loc="best")

    for axis in axes:
        axis.set_xlabel("Component 1")
        axis.set_ylabel("Component 2")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def generate_sampling_comparison(
    dataset,
    original_csv,
    sampled_csv,
    output_dir,
    *,
    dataset_name="custom",
    original_pcap=None,
    sampled_pcap=None,
    embedding_method="auto",
    max_points_per_source=1000,
    random_state=42,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    original_csv_frame = load_csv_frame(original_csv)
    sampled_csv_frame = load_csv_frame(sampled_csv)

    original_frame = prepare_feature_frame(dataset, original_csv_frame, "original")
    sampled_frame = prepare_feature_frame(dataset, sampled_csv_frame, "sampled")
    comparison_frame = pd.concat([original_frame, sampled_frame], ignore_index=True)
    embedding_frame = sample_embedding_frame(comparison_frame, max_points_per_source, random_state)
    embedding, embedding_method_used = compute_embedding(
        embedding_frame,
        embedding_method=embedding_method,
        random_state=random_state,
    )

    plot_ratio_comparison(
        original_frame,
        sampled_frame,
        "label",
        output_dir / "label_ratio.png",
        "Benign / Malicious Ratio",
    )
    plot_ratio_comparison(
        original_frame,
        sampled_frame,
        "protocol_display",
        output_dir / "protocol_ratio.png",
        "Protocol Distribution",
    )
    plot_histogram_comparison(
        original_frame,
        sampled_frame,
        "flow_duration_seconds",
        output_dir / "flow_duration_histogram.png",
        "Flow Duration Comparison",
        "Flow Duration (seconds)",
    )
    plot_histogram_comparison(
        original_frame,
        sampled_frame,
        "timestamp_epoch",
        output_dir / "timestamp_histogram.png",
        "Timestamp Distribution",
        "Timestamp (epoch seconds)",
    )
    plot_embedding(
        embedding_frame,
        embedding,
        output_dir / "embedding.png",
        embedding_method_used,
    )

    report = build_report(dataset_name, original_frame, sampled_frame, embedding_method_used)
    if original_pcap is not None and sampled_pcap is not None:
        original_packet_count = count_pcap_packets(original_pcap)
        sampled_packet_count = count_pcap_packets(sampled_pcap)
        report["original_pcap_packets"] = original_packet_count
        report["sampled_pcap_packets"] = sampled_packet_count
        plot_packet_count_comparison(original_packet_count, sampled_packet_count, output_dir / "packet_count.png")
    save_report(report, output_dir)
    return report


def build_argument_parser():
    parser = argparse.ArgumentParser(description="Compare original and sampled preprocessing CSV files.")
    parser.add_argument("--dataset", required=True, choices=sorted(DATASET_PRESETS))
    parser.add_argument("--original-dir")
    parser.add_argument("--sampled-dir")
    parser.add_argument("--original-csv")
    parser.add_argument("--sampled-csv")
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--original-pcap")
    parser.add_argument("--sampled-pcap")
    parser.add_argument("--embedding-method", choices=["auto", "tsne", "pca"], default="auto")
    parser.add_argument("--max-points-per-source", type=int, default=1000)
    parser.add_argument("--random-state", type=int, default=42)
    return parser


def main():
    parser = build_argument_parser()
    args = parser.parse_args()
    if (args.original_dir is None) != (args.sampled_dir is None):
        parser.error("--original-dir and --sampled-dir must be provided together")

    if args.original_dir and args.sampled_dir:
        original_csv, detected_original_pcap = resolve_csv_pcap_from_dir(args.original_dir, csv_required=True, pcap_required=False, sampled=False)
        sampled_csv, detected_sampled_pcap = resolve_csv_pcap_from_dir(args.sampled_dir, csv_required=True, pcap_required=False, sampled=True)
        original_pcap = args.original_pcap or (str(detected_original_pcap) if detected_original_pcap else None)
        sampled_pcap = args.sampled_pcap or (str(detected_sampled_pcap) if detected_sampled_pcap else None)
    else:
        if not args.original_csv or not args.sampled_csv:
            parser.error("either provide --original-dir/--sampled-dir or provide --original-csv/--sampled-csv")
        original_csv = args.original_csv
        sampled_csv = args.sampled_csv
        original_pcap = args.original_pcap
        sampled_pcap = args.sampled_pcap

    dataset = build_dataset_from_preset(args.dataset)
    report = generate_sampling_comparison(
        dataset,
        original_csv=str(original_csv),
        sampled_csv=str(sampled_csv),
        output_dir=args.output_dir,
        dataset_name=args.dataset,
        original_pcap=original_pcap,
        sampled_pcap=sampled_pcap,
        embedding_method=args.embedding_method,
        max_points_per_source=args.max_points_per_source,
        random_state=args.random_state,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
