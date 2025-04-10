import os
import glob
from scapy.all import PcapReader, PcapWriter
import random 
import os.path
import csv
from scapy.all import PcapReader
import pandas as pd
from datetime import datetime
from tqdm import tqdm
from dateutil import parser
from data_preprocessing.utils import Dataset


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
        self.labels_files.insert(0, os.path.join(self.base_dir, self.feature_names_file))

        with open(self.combined_csv, "w", newline="", encoding="utf-8") as output_csv:
            writer = csv.writer(output_csv) 
            for path in self.labels_files:
                print(f"Now processing {path}")
                with open(path, "r", encoding="latin1") as input_csv:
                    reader = csv.reader(input_csv)
                    if not header_values:
                        print("Discovered header not included yet...")
                        # skip header
                        _header = next(reader)
                        for row in reader:
                            feature_name = row[1]
                            header_values.append(feature_name)
                        writer.writerow(header_values)
                    else:
                        for row in reader:
                            corrected_row = self.correct_csv_row(row)
                            writer.writerow(corrected_row)
        print(f"Combined CSV written to {self.combined_csv}")


    def test_pcap_against_csv(self, pcap_glob_patterns, csv_path ):
        """
        Tests a randomly selected PCAP file to see if its packets correlate with entries in a CSV.

        Args:
            pcap_glob_patterns (List[str]): List of glob patterns to locate PCAP files.
            csv_path (str): Path to the CSV file for correlation.

        Returns:
            None
        """
        test_files = []
        for pattern in pcap_glob_patterns:
            full_pattern = os.path.join(self.base_dir, pattern)
            test_files.extend(glob.glob(full_pattern))
        if not test_files:
            print("No pcap files found for testing.")
            return

        test_file = random.choice(test_files)
        print(f"Testing pcap file: {test_file}")

        csv_records = self.transform_csv_to_dict( os.path.join(self.base_dir, csv_path))
        assignable = 0
        unassignable = 0
        print("Iterating over the pcap...")
        with PcapReader(test_file) as reader:
            number_of_packets = 0
            for pkt in tqdm(reader, desc="Processing packets"):
                number_of_packets += 1
                if self.get_packet_matches_of_csv(pkt, csv_records):
                    assignable += 1
                else:
                    unassignable += 1
                
        print("Done testing pcap vs CSV")
        print(f"PCAP got {number_of_packets} packets")
        print(f"Got {assignable} assignable, {unassignable} unassignable packets. Ratio: {assignable/unassignable}")

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
            for pattern in self.pcap_path_pattern:
                files = glob.glob(os.path.join(self.base_dir, pattern))
                for pcap_file in files:
                    print(f"Reading from {pcap_file}")
                    with PcapReader(pcap_file) as reader:
                        for packet in tqdm(reader, desc=f"Packets of file {pcap_file}"):                        
                            writer.write(packet)
        print(f"Combined pcap written to {self.combined_pcap}")

            
    def sample_pcap_and_filter_csv(self, pcap_path, pcap_output_path, csv_path, output_csv, sample_size=10000):
        """
        Samples packets from a PCAP file and filters corresponding rows in the CSV.

        Args:
            pcap_path (str): Path to the input PCAP file.
            pcap_output_path (str): Path to the output sampled PCAP file.
            csv_path (str): Path to the full CSV file.
            output_csv (str): Path to the output filtered CSV file.
            sample_size (int, optional): Number of packets to sample. Defaults to 10000.

        Returns:
            None
        """
        print(f"Sampling {sample_size} from {pcap_path}...")
        samples = []
        with PcapWriter(pcap_output_path, append=False) as pcap_writer:
            with PcapReader(pcap_path) as reader:
                for i, pkt in enumerate(reader):
                    samples.append(pkt)
                    pcap_writer.write(pkt)
                    if len(samples) >= sample_size:
                        break
        print(f"Extracted {len(samples)} packets.")

        print(f"Loading CSV {csv_path}...")
        csv_records = self.transform_csv_to_dict(csv_path)

        print("Filtering CSV...")
        matches = {}
        for pkt in tqdm(samples, total=sample_size, desc="Sampling process"):
            match = self.get_packet_matches_of_csv(pkt, csv_records)
            if match:
                matches[match] = True

        if matches:
            matching_rows = 0
            with open(output_csv, "w") as sampled_csv:
                writer = csv.writer(sampled_csv)
                with open(csv_path, "r") as input_csv:
                    reader = csv.reader(input_csv)
                    header = next(reader)
                    writer.writerow(header)
                    for row in reader:
                        key = self.get_key_from_csv_row(row=row)
                        if key in matches:
                            writer.writerow(row)
                            matching_rows += 1
            print(f"Found {matching_rows} matching rows.")
            print(f"Filtered CSV written to: {output_csv}")
        else:
            print("No matches found.")

    def correct_csv_row(self, row):
        corrected_row = row
        if row[self.labels_row] == 0:
            corrected_row[self.labels_row] = "Benign"
        else:
            corrected_row[self.labels_row] = "Malicious"
        start_time_human_readable = datetime.fromtimestamp(int(row[28])).strftime("%Y-%m-%d %H:%M:%S")
        corrected_row[self.ts_row] = start_time_human_readable 
        return corrected_row

if __name__ == "__main__":

    unsbw = UNSBW(
        sip_row=0,
        sport_row=1,
        dip_row=2,
        dport_row=3,
        labels_row=-1,
        ts_row=28,
        base_dir_path="/home/sftpuser/uploads/master/unsw-nb15/",
        labels_path_glob=[ 
            "labels/UNSW-NB15_1.csv", 
            "labels/UNSW-NB15_2.csv", 
            "labels/UNSW-NB15_3.csv", 
            "labels/UNSW-NB15_4.csv" 
        ],
        pcap_path_glob=["pcaps/1/*.pcap", "pcaps/2/*.pcap" ],
        combined_csv="./data_preprocessing/unsw_nb15/combined-class-test.csv",
        combined_pcap="./data_preprocessing/unsw_nb15/combined-class-test.pcap"
    )

    # unsbw.combine_csvs()
    # unsbw.pcap_path_pattern = ["pcaps/2/1.pcap", "pcaps/2/3.pcap"]
    # unsbw.combine_pcaps()

    all_pcap_files = []
    full_pattern = os.path.join(unsbw.base_dir, unsbw.pcap_path_pattern[0])
    all_pcap_files.extend(glob.glob(full_pattern))

    unsbw.sample_pcap_and_filter_csv(
        pcap_output_path="data_preprocessing/unsw_nb15/sample_10000.pcap",
        pcap_path=random.choice(all_pcap_files),
        csv_path="data_preprocessing/unsw_nb15/combined.csv",
        output_csv="data_preprocessing/unsw_nb15/sample_10000.csv",
        sample_size=10000
     )

    # nsbw.base_dir = "./data_preprocessing/unsw_nb15/"
    # unsbw.test_pcap_against_csv(["sample_1000.pcap"], "sample_1000.csv")
