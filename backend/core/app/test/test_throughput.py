from unittest.mock import patch

import pytest

from app.throughput import (
    ThroughputProfile,
    _payload_bytes,
    _port_for_packet,
    _run_iperf,
)


def test_payload_bytes_pads_and_truncates_deterministically():
    assert _payload_bytes("abc", 5) == b"abcXX"
    assert _payload_bytes("abcdef", 3) == b"abc"
    assert _payload_bytes(None, 4) == b"XXXX"


def test_port_for_packet_stays_in_ephemeral_range():
    ports = [_port_for_packet(65534, index) for index in range(4)]

    assert ports == [65534, 65535, 1024, 1025]


def test_run_iperf_requires_iperf3():
    profile = ThroughputProfile(traffic_mode="iperf")

    with patch("app.throughput.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="iperf3 is required"):
            _run_iperf(profile, "127.0.0.1")


def test_run_iperf_parses_json_summary():
    profile = ThroughputProfile(
        traffic_mode="iperf",
        destination_ip="192.0.2.10",
        destination_port=5201,
        iperf_duration=1,
        iperf_parallel=2,
    )
    completed = type(
        "Completed",
        (),
        {
            "returncode": 0,
            "stdout": '{"end": {"sum_sent": {"bytes": 125000, "bits_per_second": 1000000}}}',
            "stderr": "",
        },
    )()

    with patch("app.throughput.shutil.which", return_value="/usr/bin/iperf3"):
        with patch("app.throughput.subprocess.run", return_value=completed) as run:
            result = _run_iperf(profile, "127.0.0.1")

    assert result["bytes_sent"] == 125000
    assert result["throughput_mbps"] == 1.0
    command = run.call_args.args[0]
    assert command[:4] == ["/usr/bin/iperf3", "-c", "192.0.2.10", "-t"]
    assert "-J" in command
