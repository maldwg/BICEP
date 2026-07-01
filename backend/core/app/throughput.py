from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from scapy.all import ICMP, IP, TCP, UDP, Raw, send
from app.models.benchmarking import (
    TRAFFIC_MODE_IPERF,
    TRAFFIC_MODE_PACKET_GENERATOR,
)


@dataclass
class ThroughputProfile:
    traffic_mode: str
    packet_count: int = 1000
    rate_pps: float = 100.0
    payload_size: int = 64
    protocol: str = "udp"
    source_ip: str | None = None
    destination_ip: str | None = None
    source_port: int = 40000
    destination_port: int = 50000
    payload: str | None = None
    iperf_duration: int = 10
    iperf_parallel: int = 1
    iperf_protocol: str = "tcp"
    iperf_bandwidth: str | None = None


async def run_throughput_traffic(
    profile: ThroughputProfile, fallback_destination_ip: str
) -> dict:
    if profile.traffic_mode == TRAFFIC_MODE_PACKET_GENERATOR:
        return await asyncio.to_thread(
            _run_packet_generator, profile, fallback_destination_ip
        )
    if profile.traffic_mode == TRAFFIC_MODE_IPERF:
        return await asyncio.to_thread(_run_iperf, profile, fallback_destination_ip)
    raise ValueError(f"Unsupported throughput traffic mode: {profile.traffic_mode}")


def _run_packet_generator(profile: ThroughputProfile, fallback_destination_ip: str) -> dict:

    destination_ip = profile.destination_ip or fallback_destination_ip
    protocol = profile.protocol.lower()
    packet_count = max(1, int(profile.packet_count or 1))
    rate_pps = max(0.0, float(profile.rate_pps or 0))
    inter_packet_delay = 1 / rate_pps if rate_pps > 0 else 0
    payload_bytes = _payload_bytes(profile.payload, profile.payload_size)
    bytes_sent = 0

    start = time.perf_counter()
    for index in range(packet_count):
        packet = IP(dst=destination_ip)
        if profile.source_ip:
            packet.src = profile.source_ip

        if protocol == "tcp":
            packet = packet / TCP(
                sport=_port_for_packet(profile.source_port, index),
                dport=profile.destination_port,
                flags="S",
            )
        elif protocol == "udp":
            packet = packet / UDP(
                sport=_port_for_packet(profile.source_port, index),
                dport=profile.destination_port,
            )
        elif protocol == "icmp":
            packet = packet / ICMP()
        else:
            raise ValueError(f"Unsupported packet protocol: {profile.protocol}")

        if payload_bytes:
            packet = packet / Raw(payload_bytes)

        bytes_sent += len(bytes(packet))
        send(packet, verbose=False)
        if inter_packet_delay > 0 and index < packet_count - 1:
            time.sleep(inter_packet_delay)

    runtime = max(time.perf_counter() - start, 0.000001)
    return {
        "packet_count": packet_count,
        "bytes_sent": bytes_sent,
        "traffic_runtime": runtime,
        "throughput_pps": packet_count / runtime,
        "throughput_mbps": (bytes_sent * 8) / runtime / 1_000_000,
    }


def _run_iperf(profile: ThroughputProfile, fallback_destination_ip: str) -> dict:
    iperf_binary = shutil.which("iperf3")
    if iperf_binary is None:
        raise RuntimeError("iperf3 is required for iperf throughput tests.")

    destination_ip = profile.destination_ip or fallback_destination_ip
    command = [
        iperf_binary,
        "-c",
        destination_ip,
        "-t",
        str(max(1, int(profile.iperf_duration or 1))),
        "-p",
        str(profile.destination_port or 5201),
        "-P",
        str(max(1, int(profile.iperf_parallel or 1))),
        "-J",
    ]
    if profile.iperf_protocol.lower() == "udp":
        command.append("-u")
        if profile.iperf_bandwidth:
            command.extend(["-b", profile.iperf_bandwidth])

    start = time.perf_counter()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=max(5, int(profile.iperf_duration or 1) + 15),
    )
    runtime = max(time.perf_counter() - start, 0.000001)
    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(error or "iperf throughput test failed.")

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("iperf did not return JSON output.") from exc

    end = result.get("end", {})
    summary = (
        end.get("sum_sent")
        or end.get("sum")
        or end.get("sum_received")
        or {}
    )
    bytes_sent = int(summary.get("bytes") or 0)
    bits_per_second = float(summary.get("bits_per_second") or 0)
    packet_count = summary.get("packets")
    throughput_pps = (
        float(packet_count) / runtime
        if packet_count is not None and runtime > 0
        else None
    )

    return {
        "packet_count": int(packet_count) if packet_count is not None else None,
        "bytes_sent": bytes_sent,
        "traffic_runtime": runtime,
        "throughput_pps": throughput_pps,
        "throughput_mbps": bits_per_second / 1_000_000,
    }


def _payload_bytes(payload: str | None, payload_size: int) -> bytes:
    requested_size = max(0, int(payload_size or 0))
    if payload:
        data = payload.encode("utf-8")
    else:
        data = b"X" * requested_size
    if requested_size == 0:
        return b""
    if len(data) >= requested_size:
        return data[:requested_size]
    return data + (b"X" * (requested_size - len(data)))


def _port_for_packet(base_port: int, index: int) -> int:
    base = int(base_port or 40000)
    return 1024 + ((base + index - 1024) % (65535 - 1024 + 1))
