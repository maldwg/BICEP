import os
import glob
from scapy.all import PcapReader, PcapWriter
import random 
import os.path
import csv
from scapy.all import PcapReader
from datetime import datetime, timedelta, timezone
from tqdm import tqdm
from data_preprocessing.utils import Dataset, Precision, csv_row_is_empty


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
                            corrected_pkt = self.correct_pcap_pkt(packet)
                            writer.write(corrected_pkt)
        print(f"Combined pcap written to {self.combined_pcap}")



    def correct_pcap_pkt(self, pkt):
        
        def adjust_time_offset(pkt_time):
            time_offset = timedelta(hours=1)
            adjusted_time = pkt_time + time_offset
            return adjusted_time.strftime(self.human_readable_timestamp_format)

        corrected_pkt = pkt
        pkt_time = datetime.fromtimestamp(float(pkt.time))
        adjusted_time_str = adjust_time_offset(pkt_time)
        parsed_datetime = datetime.strptime(adjusted_time_str, self.human_readable_timestamp_format).replace(tzinfo=timezone.utc)
        
        unix_timestamp = parsed_datetime.timestamp()
        test = datetime.fromtimestamp(unix_timestamp , timezone.utc).replace(tzinfo=None).isoformat()
        corrected_pkt.time = unix_timestamp
        # print(f"original: {pkt_time} - updated: {parsed_datetime} - updated from ts: {test}")
        return corrected_pkt


            
    # def sample_pcap_and_filter_csv(self, pcap_path, pcap_output_path, csv_path, output_csv, sample_size=10000):
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
    #     print(f"Sampling {sample_size} from {pcap_path}...")
    #     samples = []
    #     with PcapWriter(pcap_output_path, append=False) as pcap_writer:
    #         with PcapReader(pcap_path) as reader:
    #             for i, pkt in enumerate(reader):
    #                 samples.append(pkt)
    #                 pcap_writer.write(pkt)
    #                 if len(samples) >= sample_size:
    #                     break
    #     print(f"Extracted {len(samples)} packets.")

    #     print(f"Loading CSV {csv_path}...")
    #     csv_records = self.transform_csv_to_dict(csv_path)

    #     print("Filtering CSV...")
    #     matches = {}
    #     for pkt in tqdm(samples, total=sample_size, desc="Sampling process"):
    #         match = self.get_packet_matches_of_csv(pkt, csv_records)
    #         if match:
    #             matches[match] = True

    #     if matches:
    #         matching_rows = 0
    #         with open(output_csv, "w") as sampled_csv:
    #             writer = csv.writer(sampled_csv)
    #             with open(csv_path, "r") as input_csv:
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
        base_dir_path="/mnt/hdd/Datasets/unsw-nb15/",
        labels_path_glob=[ 
            "labels/UNSW-NB15_1.csv", 
            "labels/UNSW-NB15_2.csv", 
            "labels/UNSW-NB15_3.csv", 
            "labels/UNSW-NB15_4.csv" 
        ],
        pcap_path_glob=["pcaps/1/*.pcap", "pcaps/2/*.pcap" ],
        combined_csv="/mnt/hdd/Datasets/unsw-nb15/combined.csv",
        combined_pcap="/mnt/hdd/Datasets/unsw-nb15/combined.pcap",
        precision=Precision.MILISECOND.value
    )

    # unsbw.combine_csvs()

    unsbw.combine_pcaps()
    # unsbw.sample_subset_of_combined_files(
    #      output_csv_file= "/mnt/hdd/Datasets/unsw-nb15/sampled-ratio-0point5-percent.csv", 
    #      output_pcap_file="/mnt/hdd/Datasets/unsw-nb15/sampled-ratio-0point5-percent.pcap",
    #      ratio=0.005
    #  )
    # unsbw.sample_pcap_and_filter_csv_from_combined(
    #   output_csv="/mnt/hdd/Datasets/unsw-nb15/sampled.csv",
    #   output_pcap= "/mnt/hdd/Datasets/unsw-nb15/sampled.pcap",
    #   sample_ratio=0.001,
    #)

    #unsbw.write_class_ratios_from_combined_csv_to_file("./data_preprocessing/unsw_nb15/ratio.txt")
    #unsbw.write_noise_ratios_from_combined_pcap_to_file("./data_preprocessing/unsw_nb15/noise_ratio.txt")