import os
from pathlib import Path

import scapy.config as scapy_config


# Keep Scapy caches in writable temp locations during sandboxed test runs.
_SCAPY_CACHE_ROOT = Path("/tmp/scapy-cache")
_SCAPY_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(_SCAPY_CACHE_ROOT))

_original_set_conf_sockets = scapy_config._set_conf_sockets
scapy_config.conf.route_autoload = False
scapy_config.conf.route6_autoload = False


def _sandbox_safe_set_conf_sockets():
    original_reload = scapy_config.conf.ifaces.reload
    scapy_config.conf.ifaces.reload = lambda: None
    try:
        return _original_set_conf_sockets()
    finally:
        scapy_config.conf.ifaces.reload = original_reload


scapy_config._set_conf_sockets = _sandbox_safe_set_conf_sockets


def pytest_addoption(parser):
    parser.addoption(
        "--plot-dataset",
        action="store",
        default=None,
        help=(
            "Single dataset name for comparison plotting, e.g. cic_ids_2017. "
            "Defaults to BICEP_PLOT_DATASET when set."
        ),
    )
    parser.addoption(
        "--plot-data-root",
        action="store",
        default=None,
        help=(
            "Root directory containing per-dataset folders with "
            "original/sample.csv + sample.pcap and sampled/plots output dirs. "
            "Defaults to BICEP_PLOT_DATA_ROOT or the repo tests/data folder."
        ),
    )
    parser.addoption(
        "--plot-datasets",
        action="store",
        default=None,
        help=(
            "Comma-separated dataset names for comparison plot tests. "
            "Defaults to BICEP_PLOT_DATASETS or all supported datasets."
        ),
    )
    parser.addoption(
        "--plot-original-dir",
        action="store",
        default=None,
        help=(
            "Directory containing the original CSV/PCAP pair. "
            "Use together with --plot-sampled-dir and --plot-dataset."
        ),
    )
    parser.addoption(
        "--plot-sampled-dir",
        action="store",
        default=None,
        help=(
            "Directory containing the sampled CSV/PCAP pair, or an empty directory "
            "where the test can write flow_based_sample.* outputs."
        ),
    )
    parser.addoption(
        "--plot-output-dir",
        action="store",
        default=None,
        help=(
            "Directory where plots should be written. Defaults to the current working "
            "directory when using --plot-original-dir/--plot-sampled-dir."
        ),
    )
