from scapy.all import PcapReader, PcapWriter
import csv
from datetime import datetime
from dateutil import parser 
import os
import os.path

class Dataset():
    def __init__(self, sip_row, sport_row, dip_row, dport_row, labels_row, ts_row, base_dir_path, labels_path_glob, pcap_path_glob, combined_csv, combined_pcap ):
        self.sip_row = sip_row
        self.sport_row= sport_row
        self.dip_row = dip_row
        self.dport_row = dport_row
        self.labels_row = labels_row
        self.ts_row = ts_row
        self.base_dir = base_dir_path
        self.labels_path = labels_path_glob
        self.pcap_path_pattern = pcap_path_glob
        # Output paths
        self.combined_csv = combined_csv
        self.combined_pcap = combined_pcap
        self.labels_files = [ os.path.join(self.base_dir, file) for file in self.labels_path]

    def get_key_from_csv_row(self, row):
        """
        Extracts a unique key from a CSV row based on timestamp, IPs, and ports.

        Args:
            row (List[str]): A row from the CSV.

        Returns:
            tuple: Key in the format (timestamp, src_ip, src_port, dst_ip, dst_port).
        """
        src_ip = str(row[self.sip_row])
        src_port = str(row[self.sport_row])
        dest_ip = str(row[self.dip_row])
        dest_port = str(row[self.dport_row])
        try:
            timestamp = datetime.fromtimestamp(row[self.ts_row]).strftime("%Y-%m-%d %H:%M:%S") 
        except Exception as e:
            timestamp = parser.parse(row[self.ts_row], dayfirst=False).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S')
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
                    timestamp = timestamp = datetime.fromtimestamp(float(pkt.time)).strftime("%Y-%m-%d %H:%M:%S") 
                    srcip = str(ip_layer.src)
                    sport = str(transport.sport)
                    dstip = str(ip_layer.dst)
                    dsport = str(transport.dport)
                    return (timestamp, srcip, sport, dstip, dsport)
        except Exception as e:
            pass
        return None



    def get_packet_matches_of_csv(self, pkt, csv_records):
        """
        Checks whether a given packet matches any record in the CSV records.

        Args:
            pkt (Packet): Scapy packet to match.
            csv_records (dict): Dictionary of CSV keys.

        Returns:
            tuple or None: Matching key if found, otherwise None.
        """
        key = self.extract_key_from_pcap_packet(pkt)
        if key:
            if key in csv_records:
                #print("key existing in csv")
                #print(key)
                return key
            # else:
            #     print("key found but not in records")
            #     print(key)
        else:
            #print("key-not-found")
            #print(key)
            return None
        

