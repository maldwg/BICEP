import os
import glob
import random 
import os.path
import csv
from datetime import datetime, timedelta, timezone
from tqdm import tqdm
from data_preprocessing.utils import Dataset, Precision, csv_row_is_empty
from scapy.all import *
from scapy.layers.l2 import CookedLinux, Ether, ARP
from scapy.layers.inet import IP
from scapy.packet import Raw
from scapy.layers.inet6 import IPv6 

class UNSBW(Dataset):

    feature_names_file =  "labels/NUSW-NB15_features.csv"

    def combine_csvs(self):
        """
        Combines multiple CSV files into a single output file.
        Returns:
            None
        """
        # ensure that header get processed too
        header_values = []
        # always insert at position 0 to vbe able to include the headers reliably
        self.labels_files.insert(0, os.path.join(self.base_dir, self.feature_names_file))

        with open(self.combined_csv, "w", newline="", encoding="utf-8") as output_csv:
            writer = csv.writer(output_csv) 
            for path in self.labels_files:
                print(f"Now processing {path}")
                with open(path, "r", encoding="latin1") as input_csv:
                    reader = csv.reader(input_csv)
                    if not header_values:
                        print("Discovered header not included yet...")
                        _header = next(reader)
                        for row in reader:
                            feature_name = row[1]
                            header_values.append(feature_name)
                        writer.writerow(header_values)
                    else:
                        for row in reader:
                            if csv_row_is_empty(row):
                                continue
                            corrected_row = self.correct_csv_row(row)
                            if self.csv_row_contains_invalid_information(corrected_row):
                                continue
                            writer.writerow(corrected_row)
        print(f"Combined CSV written to {self.combined_csv}")

    def combine_pcaps(self):
        """
        Combines multiple PCAP files into one output PCAP.

        Args:
            pcap_globs (List[str]): List of glob patterns pointing to PCAP files.
            output_pcap_path (str): Output path for the combined PCAP file.

        Returns:
            None
        """
        with PcapWriter(self.combined_pcap, append=True) as writer:
                for pcap_file in self.pcap_files:
                    print(f"Reading from {pcap_file}")
                    with PcapReader(pcap_file) as reader:
                        for packet in tqdm(reader, desc=f"Packets of file {pcap_file}"):                        
                            # corrected_pkt = self.correct_pcap_pkt(packet, timedelta(hours=2))
                            writer.write(self.sll_to_ether(packet))
        print(f"Combined pcap written to {self.combined_pcap}")


    def correct_csv_row(self, row):
        corrected_row = row
        try:
            if int(row[self.labels_row]) == 0:
                corrected_row[self.labels_row] = "Benign"
            else:
                corrected_row[self.labels_row] = "Malicious"
        except Exception as e:
            corrected_row[self.labels_row] = "Benign"
        start_time = datetime.fromtimestamp(int(row[28])) + timedelta(hours=-1)
        start_time_human_readable = start_time.strftime("%Y-%m-%d %H:%M:%S")
        # print(f"orig time: {datetime.fromtimestamp(int(row[28]))} - corrected time {start_time_human_readable}")

        corrected_row[self.ts_row] = start_time_human_readable       
        
        return corrected_row



    def sll_to_ether(self,pkt):
        if not pkt.haslayer(CookedLinux):
            return pkt

        payload = pkt[CookedLinux].payload
        ether_type = 0x0000

        if payload.haslayer(IP):
            ether_type = 0x0800
        elif payload.haslayer(IPv6):
            ether_type = 0x86DD
        elif payload.haslayer(ARP):
            ether_type = 0x0806
        else:
            return Ether(
                src="12:34:56:78:90:ab", 
                dst="ab:cd:ef:12:34:56", 
                type=0x0000
            ) / Raw(load=bytes(payload))

        return Ether(
            src="12:34:56:78:90:ab", 
            dst="ab:cd:ef:12:34:56", 
            type=ether_type
    ) / payload


if __name__ == "__main__":

    unsbw = UNSBW(
        sip_row=0,
        sport_row=1,
        dip_row=2,
        dport_row=3,
        labels_row=-1,
        ts_row=28,
        base_dir_path="/mnt/hdd/Datasets/unsw-nb15/",
        labels_path_glob=[ 
            "labels/UNSW-NB15_1.csv", 
            "labels/UNSW-NB15_2.csv", 
            "labels/UNSW-NB15_3.csv", 
            "labels/UNSW-NB15_4.csv" 
        ],
        pcap_path_glob=["pcaps/1/*.pcap", "pcaps/2/*.pcap" ],
        combined_csv="/mnt/hdd/Datasets/unsw-nb15/combined_filtered.csv",
        combined_pcap="/mnt/hdd/Datasets/unsw-nb15/combined_no_sll.pcap",
        precision=Precision.MILISECOND.value
    )

    unsbw.combine_csvs()
    # unsbw.combine_pcaps()
    # unsbw.sample_subset_of_combined_files(
    #      output_csv_file= "/mnt/hdd/Datasets/unsw-nb15/sampled-ratio-0point5-percent.csv", 
    #      output_pcap_file="/mnt/hdd/Datasets/unsw-nb15/sampled-ratio-0point5-percent.pcap",
    #      ratio=0.005
    #  )
    
    #unsbw.write_class_ratios_from_combined_csv_to_file("./data_preprocessing/unsw_nb15/ratio.txt")
    # unsbw.write_noise_ratios_from_combined_pcap_to_file("./data_preprocessing/unsw_nb15/noise_ratio.txt")
    
    # unsbw.sample_from_csv_and_include_pcap_flow_based(
    #   output_csv="/mnt/hdd/Datasets/unsw-nb15/sampling_retry.csv",
    #   output_pcap= "/mnt/hdd/Datasets/unsw-nb15/sampling_retry.pcap",
    #     sample_ratio_benign    = 0.00225,
    #     sample_ratio_malicious = 0.0125
    # )
