from dataclasses import dataclass
import socket
import struct

from scapy.all import PcapReader, PcapWriter, RawPcapReader, RawPcapWriter
import csv
from datetime import datetime, timedelta, timezone
from dateutil import parser 
import random
import os
import os.path
import glob
import time
from enum import Enum
from tqdm import tqdm
import ipaddress


@dataclass
class FlowWindow:
    row_index: int
    row: list
    flow_key: tuple
    protocol: str | None
    start: datetime
    end: datetime


class Precision(Enum):
    HOUR = "hour"
    MINUTE = "minute"
    SECOND = "second"
    MILISECOND = "milisecond" 
class Dataset():
    def __init__(
        self,
        sip_row,
        sport_row,
        dip_row,
        dport_row,
        labels_row,
        ts_row,
        base_dir_path,
        labels_path_glob,
        pcap_path_glob,
        combined_csv,
        combined_pcap,
        precision,
        protocol_row=None,
        flow_duration_row=None,
        flow_duration_unit="seconds",
        sampled_csv=None,
        sampled_pcap=None,
    ):
        self.sip_row = sip_row
        self.sport_row= sport_row
        self.dip_row = dip_row
        self.dport_row = dport_row
        self.labels_row = labels_row
        self.ts_row = ts_row
        self.protocol_row = protocol_row
        self.flow_duration_row = flow_duration_row
        self.flow_duration_unit = str(flow_duration_unit).lower()
        self.base_dir = base_dir_path
        self.labels_path = labels_path_glob
        # Output paths
        self.combined_csv = combined_csv
        self.combined_pcap = combined_pcap
        sampled_csv=sampled_csv,
        sampled_pcap=sampled_pcap,
        
        labels_files = []
        for pattern in self.labels_path:
            full_pattern = os.path.join(self.base_dir, pattern)
            labels_files.extend(glob.glob(full_pattern))
        self.labels_files = labels_files

        pcap_files = []
        for pattern in pcap_path_glob:
            full_pattern = os.path.join(self.base_dir, pattern)
            pcap_files.extend(glob.glob(full_pattern))
        self.pcap_files = pcap_files            

        self.human_readable_timestamp_format = "%Y-%m-%d %H:%M:%S.%f"


        self.precision = precision

    def parse_csv_timestamp_value(self, raw_timestamp):
        try:
            return datetime.fromtimestamp(float(raw_timestamp)).replace(tzinfo=None)
        except Exception:
            return parser.parse(str(raw_timestamp), dayfirst=False).replace(tzinfo=None)

    def get_protocol_from_csv_row(self, row):
        if self.protocol_row is None:
            return None
        return normalize_protocol_value(row[self.protocol_row])

    def get_flow_duration_seconds(self, row):
        if self.flow_duration_row is None:
            return 0.0

        raw_duration = str(row[self.flow_duration_row]).strip()
        if raw_duration == "":
            return 0.0

        try:
            duration = float(raw_duration)
        except ValueError:
            return 0.0

        if duration < 0:
            return 0.0

        if self.flow_duration_unit == "microseconds":
            return duration / 1_000_000
        if self.flow_duration_unit == "milliseconds":
            return duration / 1_000
        if self.flow_duration_unit == "nanoseconds":
            return duration / 1_000_000_000
        return duration

    def get_precision_window(self):
        if self.precision == Precision.MINUTE.value:
            return timedelta(minutes=1)
        if self.precision == Precision.HOUR.value:
            return timedelta(hours=1)
        return timedelta(seconds=1)

    def get_bidirectional_flow_key(self, src_ip, src_port, dest_ip, dest_port):
        left = (str(src_ip).strip(), str(src_port).strip())
        right = (str(dest_ip).strip(), str(dest_port).strip())
        return tuple(sorted((left, right)))

    def build_flow_window_from_csv_row(self, row, row_index):
        start = self.parse_csv_timestamp_value(row[self.ts_row])
        duration = timedelta(seconds=self.get_flow_duration_seconds(row))
        return FlowWindow(
            row_index=row_index,
            row=row,
            flow_key=self.get_bidirectional_flow_key(
                row[self.sip_row],
                row[self.sport_row],
                row[self.dip_row],
                row[self.dport_row],
            ),
            protocol=self.get_protocol_from_csv_row(row),
            start=start,
            end=start + self.get_precision_window() + duration,
        )

    def build_flow_lookup(self, sampled_rows):
        flow_lookup = {}
        for row_index, row in enumerate(sampled_rows):
            flow_window = self.build_flow_window_from_csv_row(row=row, row_index=row_index)
            flow_lookup.setdefault(flow_window.flow_key, []).append(flow_window)

        for windows in flow_lookup.values():
            windows.sort(key=lambda window: window.start)

        return flow_lookup

    def get_matching_flow_windows(self, packet_metadata, flow_lookup):
        packet_windows = flow_lookup.get(packet_metadata["flow_key"], [])
        matches = []
        for flow_window in packet_windows:
            if flow_window.protocol is not None and flow_window.protocol != packet_metadata["protocol"]:
                continue
            if flow_window.start <= packet_metadata["timestamp"] <= flow_window.end:
                matches.append(flow_window)
        return matches

    def extract_flow_metadata_from_raw_packet(self, packet_data, packet_metadata):
        packet_tuple = extract_transport_tuple_from_packet_bytes(packet_data)
        if packet_tuple is None:
            return None

        src_ip, src_port, dest_ip, dest_port, protocol = packet_tuple
        packet_timestamp = datetime.fromtimestamp(
            packet_metadata.sec + (packet_metadata.usec / 1_000_000),
            timezone.utc,
        ).replace(tzinfo=None)

        return {
            "timestamp": packet_timestamp,
            "flow_key": self.get_bidirectional_flow_key(src_ip, src_port, dest_ip, dest_port),
            "protocol": normalize_protocol_value(protocol),
        }

    def extract_keys_from_raw_packet(self, packet_data, packet_metadata):
        packet_tuple = extract_transport_tuple_from_packet_bytes(packet_data)
        if packet_tuple is None:
            return None, None

        src_ip, src_port, dest_ip, dest_port, _protocol = packet_tuple
        packet_timestamp = datetime.fromtimestamp(
            packet_metadata.sec + (packet_metadata.usec / 1_000_000),
            timezone.utc,
        ).replace(tzinfo=None)
        normalized_timestamp = normalize_timestamp(packet_timestamp, self.precision)

        forward_key = (
            normalized_timestamp,
            str(src_ip).strip(),
            str(src_port).strip(),
            str(dest_ip).strip(),
            str(dest_port).strip(),
        )
        reverse_key = (
            normalized_timestamp,
            str(dest_ip).strip(),
            str(dest_port).strip(),
            str(src_ip).strip(),
            str(src_port).strip(),
        )
        return forward_key, reverse_key

    def get_key_from_csv_row(self, row):
        """
        Extracts a unique key from a CSV row based on timestamp, IPs, and ports.

        Args:
            row (List[str]): A row from the CSV.

        Returns:
            tuple: Key in the format (timestamp, src_ip, src_port, dst_ip, dst_port).
        """
        src_ip = str(row[self.sip_row]).strip()
        src_port = str(row[self.sport_row]).strip()
        dest_ip = str(row[self.dip_row]).strip()
        dest_port = str(row[self.dport_row]).strip()
        timestamp = self.parse_csv_timestamp_value(row[self.ts_row])
        timestamp = normalize_timestamp(timestamp, self.precision)
        key = (timestamp, src_ip, src_port, dest_ip, dest_port)
        return key

    def transform_csv_to_dict(self, csv_path):
        """
        Transforms a CSV file into a dictionary with keys derived from each row.

        Args:
            csv_path (str): Path to the CSV file.

        Returns:
            dict: Dictionary with extracted keys from the CSV.
        """
        csv_records = {}
        with open(csv_path, 'r') as input_csv:
            reader = csv.reader(input_csv)
            # skip header
            _ = next(reader)
            for row in reader:
                key = self.get_key_from_csv_row(row)
                csv_records[key] = True
        return csv_records

    def extract_key_from_pcap_packet(self, pkt):
        """
        Extracts a unique ID as key from each packet if possible

        Args:
            pkt (Packet): Scapy packet.

        Returns:
            tuple or None: Key if extraction is successful, otherwise None.
        """
        try:
            if pkt.haslayer("IP") or pkt.haslayer("IPv6"):
                ip_layer = pkt["IP"] if pkt.haslayer("IP") else pkt["IPv6"]
                transport = pkt.getlayer("TCP") or pkt.getlayer("UDP")
                if transport:
                    # timestamp = datetime.fromtimestamp(float(pkt.time)).replace(tzinfo=None)  
                    # trim accordingly!              
                    timestamp = datetime.fromtimestamp(float(pkt.time), timezone.utc).replace(tzinfo=None)
                    timestamp = normalize_timestamp(timestamp, self.precision)    
                    srcip = str(ip_layer.src).strip()
                    sport = str(transport.sport).strip()
                    dstip = str(ip_layer.dst).strip()
                    dsport = str(transport.dport).strip()
                    return (timestamp, srcip, sport, dstip, dsport)
        except Exception as e:
            pass
        return None

    def extract_key_from_reverse_pcap_packet(self, pkt):
        """
        Extracts a unique ID as key from each packet if possible

        Args:
            pkt (Packet): Scapy packet.

        Returns:
            tuple or None: Key if extraction is successful, otherwise None.
        """
        try:
            if pkt.haslayer("IP") or pkt.haslayer("IPv6"):
                ip_layer = pkt["IP"] if pkt.haslayer("IP") else pkt["IPv6"]
                transport = pkt.getlayer("TCP") or pkt.getlayer("UDP")
                if transport:
                    # timestamp = datetime.fromtimestamp(float(pkt.time)).replace(tzinfo=None)  
                    # trim accordingly!              
                    timestamp = datetime.fromtimestamp(float(pkt.time), timezone.utc).replace(tzinfo=None)
                    timestamp = normalize_timestamp(timestamp, self.precision)    
                    dstip = str(ip_layer.src).strip()
                    dsport = str(transport.sport).strip()
                    srcip = str(ip_layer.dst).strip()
                    sport = str(transport.dport).strip()
                    return (timestamp, srcip, sport, dstip, dsport)
        except Exception as e:
            pass
        return None


    def get_keys_with_tolerance(self, key, precision, tolerance = 10):
        timestamp = parser.parse(key[0], dayfirst=False).replace(tzinfo=None)
        if precision == Precision.MILISECOND.value or precision == Precision.SECOND.value:
            timestamp = timestamp.replace(microsecond=0)
            timestamps_with_tolerance = [timestamp + timedelta(seconds=offset) for offset in range(-tolerance, tolerance+1)]
        else:
            timestamp = timestamp.replace(second=0, microsecond=0)
            timestamps_with_tolerance = [timestamp + timedelta(minutes=offset) for offset in range(-tolerance, tolerance+1)]
        keys = []
        for ts in timestamps_with_tolerance:
            new_key = list(key)  
            new_key[0] = normalize_timestamp(ts, precision)
            keys.append(tuple(new_key))
        return keys


    def get_packet_matches_of_csv(self, pkt, csv_records, precision=Precision.SECOND.value):
        """
        Checks whether a given packet matches any record in the CSV records.

        Args:
            pkt (Packet): Scapy packet to match.
            csv_records (dict): Dictionary of CSV keys.

        Returns:
            tuple or None: Matching key if found, otherwise None.
        """
        key = self.extract_key_from_pcap_packet(pkt)
        if key is not None:
            keys = self.get_keys_with_tolerance(key, precision, tolerance=10)
            for k in keys:
                if k in csv_records:
                    return k
        return None        

    def get_packet_matches_of_csv_reverse_packets_included(self, pkt, csv_records, precision=Precision.SECOND.value):
        """
        Checks whether a given packet matches any record in the CSV records.

        Args:
            pkt (Packet): Scapy packet to match.
            csv_records (dict): Dictionary of CSV keys.

        Returns:
            tuple or None: Matching key if found, otherwise None.
        """
        key = self.extract_key_from_pcap_packet(pkt)
        reverse_key = self.extract_key_from_reverse_pcap_packet(pkt)
        if key is not None:
            keys = self.get_keys_with_tolerance(key, precision, tolerance=10)
            for k in keys:
                if k in csv_records:
                    return k
        if reverse_key is not None:
            keys = self.get_keys_with_tolerance(reverse_key, precision, tolerance=10)
            for k in keys:
                if k in csv_records:
                    return k               
        return None     


    def get_benign_malicious_counts(self, csv_file):
        benign = 0
        malicious = 0
        with open(csv_file, 'r') as input_csv:
                reader = csv.reader(input_csv)
                header = next(reader)  # Save the header row           
                for row in reader:
                    label = row[-1]
                    if "benign" in label.casefold():
                        benign += 1
                    else:
                        malicious += 1
        return benign, malicious

    def row_is_benign(self, row):
        return "benign" in str(row[self.labels_row]).strip().casefold()

    def get_random_sampling_targets(self, csv_file, sample_ratio_benign, sample_ratio_malicious, cluster_window):
        benign = 0
        malicious = 0
        malicious_cluster_count = 0
        malicious_rows_in_current_cluster = 0
        malicious_index = 0

        with open(csv_file, "r") as input_csv:
            reader = csv.reader(input_csv)
            _header = next(reader)
            for row in reader:
                if self.row_is_benign(row):
                    benign += 1
                    continue

                malicious += 1
                malicious_rows_in_current_cluster += 1
                if malicious_index % cluster_window == 0 and malicious_index > 0:
                    malicious_cluster_count += 1
                    malicious_rows_in_current_cluster = 0
                malicious_index += 1

        if malicious_rows_in_current_cluster > 0:
            malicious_cluster_count += 1

        return (
            int(benign * sample_ratio_benign),
            int(malicious * sample_ratio_malicious),
            int(malicious_cluster_count * sample_ratio_malicious),
        )

    def reservoir_consider(self, reservoir, item, seen_items, target_size):
        if target_size <= 0:
            return
        if len(reservoir) < target_size:
            reservoir.append(item)
            return

        replacement_index = random.randint(0, seen_items - 1)
        if replacement_index < target_size:
            reservoir[replacement_index] = item

    def stream_sample_rows(self, csv_file, target_benign, target_malicious_clusters, cluster_window):
        sampled_benign = []
        sampled_malicious_clusters = []
        seen_benign = 0
        seen_malicious_clusters = 0
        malicious_index = 0
        current_cluster = []

        with open(csv_file, "r") as input_csv:
            reader = csv.reader(input_csv)
            header = next(reader)

            for row in reader:
                if self.row_is_benign(row):
                    seen_benign += 1
                    self.reservoir_consider(sampled_benign, row, seen_benign, target_benign)
                    continue

                current_cluster.append(row)
                if malicious_index % cluster_window == 0 and malicious_index > 0:
                    seen_malicious_clusters += 1
                    self.reservoir_consider(
                        sampled_malicious_clusters,
                        current_cluster[:],
                        seen_malicious_clusters,
                        target_malicious_clusters,
                    )
                    current_cluster = []
                malicious_index += 1

        if current_cluster:
            seen_malicious_clusters += 1
            self.reservoir_consider(
                sampled_malicious_clusters,
                current_cluster[:],
                seen_malicious_clusters,
                target_malicious_clusters,
            )

        sampled_malicious = [row for cluster in sampled_malicious_clusters for row in cluster]
        return header, sampled_benign, sampled_malicious


    def sample_from_csv_with_target_values(self, csv_file, target_benign, target_malicious):
        """
            sample a subset of requests from a csv file. The target values ofr benign and malicious requests
            determine how many requests are sampled.
        """
        csv_records = {}
        csv_entries_list =[]
        benign = malicious = 0
        with open(csv_file, 'r') as input_csv:
            reader = csv.reader(input_csv)
            header = next(reader)  # Save the header row   
            csv_entries_list.append(header)
            for row in reader:
                key = self.get_key_from_csv_row(row=row)             
                label = str(row[self.labels_row]).strip()
                if "benign" in label.casefold():
                    if benign < target_benign:
                        csv_records[key] = True
                        csv_entries_list.append(row)
                        benign += 1
                else:
                    if malicious < target_malicious:
                        csv_records[key] = True
                        csv_entries_list.append(row)
                        malicious += 1
                if target_malicious == malicious and target_benign == benign:
                    print("breaking cause we reached the targets")
                    print(f"Sampled {benign} benign - {malicious} malicious - wanted: {target_benign} benign abd {target_malicious} malicious")
                    break
        print(f"Sampled {benign} benign - {malicious} malicious - wanted: {target_benign} benign abd {target_malicious} malicious")
        return csv_records, csv_entries_list
    
    
    def sample_random_csv_rows(self, sample_ratio_benign, sample_ratio_malicious):
        print(f"Loading CSV {self.combined_csv}...")
        cluster_window = 5
        benign_count, malicious_count, sample_cluster_count = self.get_random_sampling_targets(
            self.combined_csv,
            sample_ratio_benign=sample_ratio_benign,
            sample_ratio_malicious=sample_ratio_malicious,
            cluster_window=cluster_window,
        )
        header, sampled_benign, sampled_malicious = self.stream_sample_rows(
            self.combined_csv,
            target_benign=benign_count,
            target_malicious_clusters=sample_cluster_count,
            cluster_window=cluster_window,
        )
        sampled_rows = sampled_benign + sampled_malicious

        print(f"Sampled {len(sampled_rows)} CSV rows (benign: {benign_count}, malicious: {malicious_count})")
        return header, sampled_rows

    def write_csv_rows(self, output_csv, header, sampled_rows):
        with open(output_csv, "w") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(sampled_rows)
        print(f"Wrote {len(sampled_rows)} sampled rows to {output_csv}")

    def sample_random_csv_lines(self, sample_ratio_benign, sample_ratio_malicious, output_csv):
        header, sampled_rows = self.sample_random_csv_rows(
            sample_ratio_benign=sample_ratio_benign,
            sample_ratio_malicious=sample_ratio_malicious,
        )
        self.write_csv_rows(output_csv=output_csv, header=header, sampled_rows=sampled_rows)
        return sampled_rows


    # Looks good to me, needs to be tested, plotted and used though ! 
    def sample_from_csv_and_include_pcap_flow_based(self, output_pcap, output_csv, sample_ratio_benign,sample_ratio_malicious, denoise=True):
        header, sampled_rows = self.sample_random_csv_rows(
            sample_ratio_benign=sample_ratio_benign,
            sample_ratio_malicious=sample_ratio_malicious,
        )
        flow_lookup = self.build_flow_lookup(sampled_rows)
        print(f"Extracting {len(sampled_rows)} sampled flows from PCAP...")

        matched_packet_count = 0
        matched_row_indices = set()
        counter = 0
        if os.path.exists(output_pcap):
            os.remove(output_pcap)
        reader = RawPcapReader(self.combined_pcap)
        writer = RawPcapWriter(output_pcap, append=False, linktype=getattr(reader, "linktype", 1), sync=True)
        try:
            for packet_data, packet_metadata in reader:
                counter += 1
                flow_metadata = self.extract_flow_metadata_from_raw_packet(packet_data, packet_metadata)
                if flow_metadata is None:
                    continue

                matching_windows = self.get_matching_flow_windows(flow_metadata, flow_lookup)
                if matching_windows:
                    if not writer.header_present:
                        writer.write_header(packet_data)
                    writer.write_packet(
                        packet_data,
                        sec=packet_metadata.sec,
                        usec=packet_metadata.usec,
                        caplen=packet_metadata.caplen,
                        wirelen=packet_metadata.wirelen,
                    )
                    matched_packet_count += 1
                    for flow_window in matching_windows:
                        matched_row_indices.add(flow_window.row_index)

                if counter % 100000 == 0 and counter > 0:
                    print(
                        f"Iterated over {counter} packets so far, "
                        f"wrote {matched_packet_count} packets from {len(matched_row_indices)} flows"
                    )
        finally:
            reader.close()
            writer.close()

        if denoise:
            matched_rows = [row for row_index, row in enumerate(sampled_rows) if row_index in matched_row_indices]
        else:
            matched_rows = sampled_rows
        self.write_csv_rows(output_csv=output_csv, header=header, sampled_rows=matched_rows)

        print(f"Written {matched_packet_count} flow packets to {output_pcap}")
        print(f"Retained {len(matched_rows)} CSV flow rows aligned with the sampled PCAP")

    def validate_sampled_data(self, csv_path=None, pcap_path=None, *, raise_on_failure=True):
        csv_path = csv_path or self.combined_csv
        pcap_path = pcap_path or self.combined_pcap

        csv_rows = []
        csv_key_lookup = {}
        with open(csv_path, "r") as csv_file:
            reader = csv.reader(csv_file)
            _header = next(reader, None)
            for row in reader:
                if csv_row_is_empty(row):
                    continue
                row_index = len(csv_rows)
                csv_rows.append(row)
                csv_key = self.get_key_from_csv_row(row)
                csv_key_lookup.setdefault(csv_key, set()).add(row_index)

        flow_lookup = self.build_flow_lookup(csv_rows)
        matched_flow_row_indices = set()
        matched_direct_key_row_indices = set()

        report = {
            "csv_path": str(csv_path),
            "pcap_path": str(pcap_path),
            "csv_rows_total": len(csv_rows),
            "csv_rows_with_flow_packet_match": 0,
            "csv_rows_without_flow_packet_match": 0,
            "csv_rows_with_direct_key_match": 0,
            "csv_rows_without_direct_key_match": 0,
            "pcap_packets_total": 0,
            "pcap_packets_transport": 0,
            "pcap_packets_matched_to_flow": 0,
            "pcap_packets_unmatched_to_flow": 0,
            "pcap_packets_unparsed": 0,
            "pcap_packets_with_direct_key_match": 0,
        }

        with RawPcapReader(str(pcap_path)) as reader:
            for packet_data, packet_metadata in reader:
                report["pcap_packets_total"] += 1

                flow_metadata = self.extract_flow_metadata_from_raw_packet(packet_data, packet_metadata)
                if flow_metadata is None:
                    report["pcap_packets_unparsed"] += 1
                    report["pcap_packets_unmatched_to_flow"] += 1
                    continue

                report["pcap_packets_transport"] += 1
                matching_windows = self.get_matching_flow_windows(flow_metadata, flow_lookup)
                if matching_windows:
                    report["pcap_packets_matched_to_flow"] += 1
                    for flow_window in matching_windows:
                        matched_flow_row_indices.add(flow_window.row_index)
                else:
                    report["pcap_packets_unmatched_to_flow"] += 1

                forward_key, reverse_key = self.extract_keys_from_raw_packet(packet_data, packet_metadata)
                packet_has_direct_key_match = False
                for candidate_key in (forward_key, reverse_key):
                    if candidate_key is None:
                        continue
                    matched_rows = csv_key_lookup.get(candidate_key)
                    if matched_rows:
                        matched_direct_key_row_indices.update(matched_rows)
                        packet_has_direct_key_match = True
                if packet_has_direct_key_match:
                    report["pcap_packets_with_direct_key_match"] += 1

        report["csv_rows_with_flow_packet_match"] = len(matched_flow_row_indices)
        report["csv_rows_without_flow_packet_match"] = report["csv_rows_total"] - len(matched_flow_row_indices)
        report["csv_rows_with_direct_key_match"] = len(matched_direct_key_row_indices)
        report["csv_rows_without_direct_key_match"] = report["csv_rows_total"] - len(matched_direct_key_row_indices)
        report["is_direct_key_compatible"] = report["csv_rows_without_direct_key_match"] == 0
        report["is_valid"] = (
            report["csv_rows_total"] > 0
            and report["pcap_packets_total"] > 0
            and report["csv_rows_without_flow_packet_match"] == 0
            and report["pcap_packets_unmatched_to_flow"] == 0
        )

        summary = (
            f"Validated sampled data for {csv_path} and {pcap_path}: "
            f"{report['csv_rows_with_flow_packet_match']}/{report['csv_rows_total']} CSV rows matched a flow window, "
            f"{report['csv_rows_with_direct_key_match']}/{report['csv_rows_total']} CSV rows matched a packet key, "
            f"{report['pcap_packets_matched_to_flow']}/{report['pcap_packets_total']} PCAP packets matched sampled flows."
        )
        print(summary)
        if raise_on_failure and not report["is_valid"]:
            raise AssertionError(
                summary
                + f" Unmatched CSV rows (flow/direct): "
                + f"{report['csv_rows_without_flow_packet_match']}/{report['csv_rows_without_direct_key_match']}; "
                + f"unmatched PCAP packets: {report['pcap_packets_unmatched_to_flow']}."
            )
        return report


# Dont use this method anymore its way to imprecise to sample around a given packet. this is not flow based, this is bad. 

    # def sample_pcap_and_filter_csv_from_combined(self, output_pcap, output_csv, sample_ratio=0.05, packet_buffer=5):
    #     """
    #     Samples packets from a PCAP file and filters corresponding rows in the CSV.

    #     Args:
    #         pcap_path (str): Path to the input PCAP file.
    #         pcap_output_path (str): Path to the output sampled PCAP file.
    #         csv_path (str): Path to the full CSV file.
    #         output_csv (str): Path to the output filtered CSV file.
    #         sample_size (int, optional): Number of packets to sample. Defaults to 10000.

    #     Returns:
    #         None
    #     """
    #     pcap_length = get_length_of_pcap(self.combined_pcap)
    #     sample_size = int(sample_ratio * pcap_length)
    #     # divide 1 by the ratio to get the absolute number of steps to take until a new sample is taken
    #     # * buffer + 1 is to sample around this modulo seleceted packet for bg traffic and special attack types which need more sample sizes
    #     # therefore we need to reduce the ammount of total modulo steps which is why sample steps needs to be bigger
    #     sample_steps = round((1 / sample_ratio) * (packet_buffer + 1))
    #     print(f"Pcap got {pcap_length} packets")
    #     print(f"Sampling {sample_size} from {self.combined_pcap}...")
    #     samples = []
    #     with PcapWriter(output_pcap, append=False) as pcap_writer:
    #         with PcapReader(self.combined_pcap) as reader:
    #             counter = 0
    #             for i, pkt in enumerate(reader):
    #                 # to not only sample only the beginngin of the file but rather all parts use the modulo
    #                 if i % sample_steps == 0:
    #                     counter = packet_buffer
    #                 # if modulo step is reached, sample the fllowing packets specified using the buffer
    #                 if counter > 0:
    #                     samples.append(pkt)
    #                     pcap_writer.write(pkt)
    #                     counter -= 1
    #                 # reset the counter again
    #                 else:
    #                     counter = 0
    #     print(f"Extracted {len(samples)} packets.")

    #     print(f"Loading CSV {self.combined_csv}...")
    #     csv_records = self.transform_csv_to_dict(self.combined_csv)

    #     print("Filtering CSV...")
    #     matches = {}
    #     for pkt in tqdm(samples, total=len(samples), desc="Sampling process"):
    #         match = self.get_packet_matches_of_csv(pkt, csv_records, self.precision)
    #         if match:
    #             matches[match] = True

    #     if matches:
    #         matching_rows = 0
    #         with open(output_csv, "w") as sampled_csv:
    #             writer = csv.writer(sampled_csv)
    #             with open(self.combined_csv, "r") as input_csv:
    #                 reader = csv.reader(input_csv)
    #                 header = next(reader)
    #                 writer.writerow(header)
    #                 for row in reader:
    #                     key = self.get_key_from_csv_row(row=row)
    #                     if key in matches:
    #                         writer.writerow(row)
    #                         matching_rows += 1
    #         print(f"Found {matching_rows} matching rows.")
    #         print(f"Filtered CSV written to: {output_csv}")
    #     else:
    #         print("No matches found.")




    def sample_subset_of_combined_files(self, output_pcap_file, output_csv_file, ratio=0.01):
        """
            Method to generate one pcap and csv file from all the dataset files. 
            A ratio can be given to reduce the amount of requests. 
            This was used to sample a given percentage from files in the dataset for slips.
            
            Baseline sampling but not 100% precise, doesn't factor in reverse keys but a tolerance interval.
        """
        print(f"filenames {output_pcap_file}")
        print(f"filenames {output_csv_file}")
        start = time.time()
        csv_entries = 0
        with open(output_csv_file, 'w') as output_csv:
            writer = csv.writer(output_csv)
            with open(self.combined_csv, 'r') as input_csv:
                benign, malicious = self.get_benign_malicious_counts(self.combined_csv)
                target_benign = int(benign*ratio)
                target_malicious = int(malicious*ratio)
                print(f"overall values: benign {benign}, malicious {malicious}")
                print(f"Target values: benign {target_benign}, malicious {target_malicious}")
                csv_records, csv_rows = self.sample_from_csv_with_target_values(self.combined_csv, target_benign, target_malicious)
                for row in csv_rows:
                    writer.writerow(row)
                    csv_entries += 1
        print(f"finished iteration and writing over CSV's after {time.time() - start} seconds")
        print("Now sampling from the pcap")

        filtered_packets = 0
        counter = 0
        with PcapWriter(output_pcap_file, append=False) as pcap_writer:
            with PcapReader(self.combined_pcap) as pcap_reader:
                for packet in pcap_reader:
                    if counter % 100000 == 0 and counter != 0:
                        print(f"processed another 100000 lines")
                        print(f"currently filtered {filtered_packets} packets")
                        print(f"took {time.time() - start} seconds until now")
                    if self.get_packet_matches_of_csv(pkt=packet, csv_records=csv_records, precision=self.precision) != None:
                        pcap_writer.write(packet)
                        filtered_packets += 1
                        if filtered_packets % 10000 == 0 and filtered_packets != 0:
                            print(f"Wrote {filtered_packets} to the file already")
                    counter += 1
        print(f"csv length: {csv_entries}, pcap length: {filtered_packets}, overall {counter} pcap requests")
        end = time.time()
        print(f"took {end-start} seconds to finish")


    def get_ts_precision(self):
        random_rows = self.get_sample_rows_from_combined_csv()
        timestamps = [ row[self.ts_row] for row in random_rows]
        if all_ts_contain(timestamps, Precision.MILISECOND.value) and ts_have_different_values(
            timestamps, Precision.MILISECOND.value
        ):
            return Precision.MILISECOND.value
        if all_ts_contain(timestamps, Precision.SECOND.value) and ts_have_different_values(
            timestamps, Precision.SECOND.value
        ):
            return Precision.SECOND.value
        if all_ts_contain(timestamps, Precision.MINUTE.value) and ts_have_different_values(
            timestamps, Precision.MINUTE.value
        ):
            return Precision.MINUTE.value
        return Precision.HOUR.value

    def get_sample_rows_from_combined_csv(self):
        with open(self.combined_csv, "r") as input:
            reader = csv.reader(input)
            _header = next(reader)
            all_rows = list(reader)
        return random.sample(all_rows, 5)

    def caluclate_noise_and_total_packets(self):
        noise_packets = 0
        total_packets = 0

        print("Calculating CSV records...")
        csv_records = self.transform_csv_to_dict(csv_path=self.combined_csv)
        
        print("Calculating noise packets")
        with PcapReader(self.combined_pcap) as pcap_reader:
            for packet in pcap_reader:
                if total_packets % 100000 == 0 and total_packets > 0:
                    print(f"iterated over {total_packets} packets")
                    print(f"had a ratio of {round(noise_packets/total_packets, 2)}")
                total_packets += 1
                # if there is no match count up noise
                if self.get_packet_matches_of_csv_reverse_packets_included(pkt=packet, csv_records=csv_records, precision=self.precision) == None:
                    noise_packets += 1      
        return noise_packets, total_packets


    def write_noise_ratios_from_combined_pcap_to_file(self, path):
        noise, total = self.caluclate_noise_and_total_packets()
        with open(path, "w") as f:
            f.write(f"Total requests: {total} \n")
            f.write(f"Noise requests: {noise} - Ratio: {round(noise/total,2)}\n")

    def write_class_ratios_from_combined_csv_to_file(self, path):
        benign, malicious = self.get_benign_malicious_counts(self.combined_csv)
        with open(path, "w") as f:
            f.write(f"Total lines: {benign+malicious} \n")
            f.write(f"Benign requests: {benign} - Ratio: {round(benign/(benign+malicious),2)}\n")
            f.write(f"Malicious requests: {malicious} - Ratio: {round(malicious/(benign+malicious),2)}")

    def correct_pcap_pkt(self, pkt, time_offset: timedelta):
        def adjust_time_offset(pkt_time, time_offset=0):
            adjusted_time = pkt_time + time_offset
            return adjusted_time.strftime(self.human_readable_timestamp_format)

        corrected_pkt = pkt
        pkt_time = datetime.fromtimestamp(float(pkt.time), tz=timezone.utc)
        adjusted_time_str = adjust_time_offset(pkt_time, time_offset)
        parsed_datetime = datetime.strptime(adjusted_time_str, self.human_readable_timestamp_format).replace(tzinfo=timezone.utc)
        
        unix_timestamp = parsed_datetime.timestamp()
        test = datetime.fromtimestamp(unix_timestamp , timezone.utc).replace(tzinfo=None).isoformat()
        corrected_pkt.time = unix_timestamp
        print(f"original: {pkt_time} tz: {pkt_time.tzinfo} - updated: {parsed_datetime} tz:  {parsed_datetime.tzinfo} - updated from ts: {test}")
        return corrected_pkt

    def csv_row_contains_invalid_information(self, row):
        key = self.get_key_from_csv_row(row=row)
        # Check for missing/empty values
        if "" in key or None in key:
            return True
        _, src_ip, src_port, d_ip, d_port = key
        # Validate IP addresses
        try:
            ipaddress.ip_address(src_ip)
            ipaddress.ip_address(d_ip)
        except ValueError:
            return True  # Invalid IP
        # Validate ports
        try:
            port1_int = int(src_port)
            port2_int = int(d_port)
            if not (0 <= port1_int <= 65535 and 0 <= port2_int <= 65535):
                return True
        except ValueError:
            return True  # Non-integer port
        return False  # Everything is valid

    def get_nan_keys_from_csv(self, csv_path):
        with open(csv_path) as input:
            reader = csv.reader(input)
            header = next(reader)
            none_rows = []
            keys = []
            for row in reader:
                key = self.get_key_from_csv_row(row=row)
                if "" in key or None in key:
                    none_rows.append(row)
                    keys.append(key)
        print(f"found {len(none_rows)} rows containing None data")
        return none_rows, keys

    # def test_pcap_against_csv(self, pcap_path, csv_path ):
    #     """
    #         dO NOT USE OR RELY ON THIS METHOD!! That is a bogous double implementation
    #     """

    #     csv_records = self.transform_csv_to_dict(csv_path)
    #     assignable = 0
    #     unassignable = 0
    #     precision = self.get_ts_precision()
    #     print(precision)
    #     print("Iterating over the pcap...")
    #     with PcapReader(pcap_path) as reader:
    #         number_of_packets = 0
    #         for pkt in tqdm(reader, desc="Processing packets"):
    #             number_of_packets += 1
    #             if self.get_packet_matches_of_csv(pkt, csv_records, precision):
    #                 assignable += 1
    #             else:
    #                 unassignable += 1
                
    #     print("Done testing pcap vs CSV")
    #     print(f"PCAP got {number_of_packets} packets")
    #     print(f"Got {assignable} assignable, {unassignable} unassignable packets. Ratio: {assignable/unassignable}")
    #     return assignable, unassignable


def normalize_protocol_value(value):
    protocol_aliases = {
        "tcp": "6",
        "udp": "17",
        "icmp": "1",
        "icmpv6": "58",
        "igmp": "2",
    }

    if value is None:
        return None

    protocol = str(value).strip().casefold()
    if protocol == "":
        return None
    if protocol in protocol_aliases:
        return protocol_aliases[protocol]

    try:
        return str(int(float(protocol)))
    except ValueError:
        return protocol


def parse_ipv4_transport_tuple(packet_data, offset):
    if len(packet_data) < offset + 20:
        return None

    version_ihl = packet_data[offset]
    version = version_ihl >> 4
    if version != 4:
        return None

    ihl = (version_ihl & 0x0F) * 4
    if len(packet_data) < offset + ihl + 4:
        return None

    protocol = packet_data[offset + 9]
    if protocol not in (6, 17):
        return None

    src_ip = socket.inet_ntoa(packet_data[offset + 12:offset + 16])
    dest_ip = socket.inet_ntoa(packet_data[offset + 16:offset + 20])
    transport_offset = offset + ihl
    src_port, dest_port = struct.unpack("!HH", packet_data[transport_offset:transport_offset + 4])
    return src_ip, src_port, dest_ip, dest_port, protocol


def parse_ipv6_transport_tuple(packet_data, offset):
    if len(packet_data) < offset + 40 + 4:
        return None

    version = packet_data[offset] >> 4
    if version != 6:
        return None

    next_header = packet_data[offset + 6]
    if next_header not in (6, 17):
        return None

    src_ip = socket.inet_ntop(socket.AF_INET6, packet_data[offset + 8:offset + 24])
    dest_ip = socket.inet_ntop(socket.AF_INET6, packet_data[offset + 24:offset + 40])
    transport_offset = offset + 40
    src_port, dest_port = struct.unpack("!HH", packet_data[transport_offset:transport_offset + 4])
    return src_ip, src_port, dest_ip, dest_port, next_header


def extract_transport_tuple_from_packet_bytes(packet_data):
    if len(packet_data) < 14:
        return None

    ether_offset = 14
    ether_type = struct.unpack("!H", packet_data[12:14])[0]

    if ether_type in (0x8100, 0x88A8):
        if len(packet_data) < 18:
            return None
        ether_type = struct.unpack("!H", packet_data[16:18])[0]
        ether_offset = 18

    if ether_type == 0x0800:
        return parse_ipv4_transport_tuple(packet_data, ether_offset)
    if ether_type == 0x86DD:
        return parse_ipv6_transport_tuple(packet_data, ether_offset)

    if len(packet_data) >= 16:
        cooked_type = struct.unpack("!H", packet_data[14:16])[0]
        if cooked_type == 0x0800:
            return parse_ipv4_transport_tuple(packet_data, 16)
        if cooked_type == 0x86DD:
            return parse_ipv6_transport_tuple(packet_data, 16)

    return None


def ts_have_different_values(timestamps, precision: str):
    
    parsed = [parse_timestamp(ts) for ts in timestamps]
    if precision == Precision.MILISECOND.value:
        print("different ms values")
        values = [ts.microsecond for ts in parsed]
    elif precision == Precision.SECOND.value:
        print("different s values")

        values = [ts.second for ts in parsed]
    elif precision == Precision.MINUTE.value:
        print("different m values")
        values = [ts.minute for ts in parsed]
    else:  # hour
        values = [ts.hour for ts in parsed]
    print(values)
    return len(set(values)) > 1

def all_ts_contain(timestamps, precision: str):
    parsed = [parse_timestamp(ts) for ts in timestamps]
    if precision == Precision.MILISECOND.value:
        print("containing ms")
        return all(ts.microsecond > 0 for ts in parsed)
    elif precision == Precision.SECOND.value:
        print("containing s")
        print(timestamps)
        return all(ts.second >= 0 for ts in parsed)
    elif precision == Precision.MINUTE.value:
        print("containing m")
        return all(ts.minute >= 0 for ts in parsed)
    else: 
        print("containing h")
        return all(ts.hour >= 0 for ts in parsed)

def parse_timestamp(timestamp):
    return parser.parse(timestamp, dayfirst=False).replace(tzinfo=None)

def normalize_timestamp(timestamp, precision):
    if precision == Precision.MILISECOND.value or precision == Precision.SECOND.value:  
        replaced_timestamp = timestamp.replace(microsecond=0)
        timestamp_format = "%Y-%m-%d %H:%M:%S"
    else:
        replaced_timestamp = timestamp.replace(second=0, microsecond=0)
        timestamp_format = "%Y-%m-%d %H:%M"
    return replaced_timestamp.strftime(timestamp_format).strip()
    
def get_length_of_pcap(pcap):
    with PcapReader(pcap) as reader:
        counter = 0
        for pkt in reader:
            counter += 1
    return counter

def csv_row_is_empty(row):
    # as long as there is one value, return that the row is not empty
    if any(row):
        return False
    return True
