import os
from scapy.all import PcapReader, PcapWriter
import os.path
import csv
from scapy.all import PcapReader
from tqdm import tqdm
from dateutil import parser 
from data_preprocessing.utils import Dataset, Precision
from datetime import timedelta, timezone, datetime

class CTU(Dataset):



    def convert_binetflow_to_csv_and_combine(self):
        """
        Converts multiple .binetflow files into CSV format and combines them.

        Returns:
            None
        """
        header_written = False
        with open(self.combined_csv, "w", newline="") as combined_csv:
            writer = csv.writer(combined_csv)
            for path in self.labels_files:
                print(f"Processing binetflow: {path}")
                with open(path, "r") as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    if not header_written:
                        writer.writerow(header)
                        header_written = True

                    for row in reader:
                        corrected_row = self.correct_csv_row(row)
                        writer.writerow(corrected_row)
        print(f"Combined binetflow CSV written to {self.combined_csv}")


    def correct_csv_row(self, row):
        """
        Corrects a single row in the UNSW-NB15 CSV file.

        Args:
            row (List[str]): A row from the CSV file.

        Returns:
            List[str]: The corrected CSV row.
        """
        corrected_row = row
        if "Normal" in row[self.labels_row] or "Background" in row[self.labels_row]:
            corrected_row[self.labels_row] = "Benign"
        else:
            corrected_row[self.labels_row] = "Malicious"
        
        start_time = parser.parse(row[0], dayfirst=False).replace(tzinfo=None).strftime(self.human_readable_timestamp_format)

        corrected_row[self.ts_row] = start_time 
               
        return corrected_row


    def combine_pcaps(self):
        """
        Combines multiple CTU-13 PCAP files into one.

        Args:
            pcap_glob_pattern (str): Glob pattern for locating PCAP files.
            output_path (str): Output PCAP path.

        Returns:
            None
        """
        with PcapWriter(self.combined_pcap, append=True) as writer:
            for file in self.pcap_files:
                print(f"Reading: {file}")
                with PcapReader(file) as reader:
                    for pkt in tqdm(reader, desc=f"Processing {os.path.basename(file)}"):
                        corrected_pkt = self.correct_pcap_pkt(pkt)
                        writer.write(corrected_pkt)
        print(f"Combined PCAP written to {self.combined_pcap}")



    def correct_pcap_pkt(self, pkt):
        
        def adjust_time_offset(pkt_time):
            time_offset = timedelta(hours=2)
            adjusted_time = pkt_time + time_offset
            return adjusted_time.strftime(self.human_readable_timestamp_format)

        corrected_pkt = pkt
        pkt_time = datetime.fromtimestamp(float(pkt.time))
        adjusted_time_str = adjust_time_offset(pkt_time)
        parsed_datetime = datetime.strptime(adjusted_time_str, self.human_readable_timestamp_format).replace(tzinfo=None)
        
        unix_timestamp = parsed_datetime.timestamp()
        corrected_pkt.time = unix_timestamp
        # print(f"original: {pkt_time} - updated: {parsed_datetime} - updated from ts: {test}")
        return corrected_pkt




    # def sample(self, pcap_path, pcap_output_path, csv_output_path, csv_path, sample_size=5000):
    #     """
    #     Samples a subset of CTU-13 dataset

    #     Args:
    #         input_path (str): Path to combined CSV.
    #         output_path (str): Where to save the sampled CSV.
    #         label_column (str): Label column name.
    #         sample_size (int): Number of rows to sample.
    #         random_seed (int): Seed for reproducibility.

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
    #         with open(csv_output_path, "w") as sampled_csv:
    #             writer = csv.writer(sampled_csv)
    #             with open(csv_path, "r") as input_csv:
    #                 reader = csv.reader(input_csv)
    #                 header = next(reader)
    #                 writer.writerow(header)
    #                 for row in reader:
    #                     # TODO remove once combined csv is created!
    #                     corrected_row = self.correct_csv_row(row)
    #                     key = self.get_key_from_csv_row(corrected_row)
    #                     if key in matches:
    #                         writer.writerow(corrected_row)
    #                         matching_rows += 1
    #         print(f"Found {matching_rows} matching rows.")
    #         print(f"Filtered CSV written to: {self.combined_csv}")
    #     else:
    #         print("No matches found.")


if __name__ == "__main__":

    ctu = CTU(
        sip_row=3,
        sport_row=4,
        dip_row=6,
        dport_row=7,
        labels_row=-1,
        ts_row=0,
        base_dir_path="/mnt/hdd/Datasets/CTU-13/",
        labels_path_glob= ["*/*.binetflow"],
        pcap_path_glob=["*/*.pcap"],
        combined_csv="/mnt/hdd/Datasets/CTU-13/combined.csv",
        combined_pcap="/mnt/hdd/Datasets/CTU-13/combined.pcap" ,
        precision=Precision.MILISECOND.value
    )

    #ctu.convert_binetflow_to_csv_and_combine()
    #ctu.combine_pcaps()
    ctu.sample_subset_of_combined_files(
        output_csv_file="/mnt/hdd/Datasets/CTU-13/sampled-ratio-0point5pc.csv",
        output_pcap_file="/mnt/hdd/Datasets/CTU-13/sampled-ratio-0point5pc.pcap",
        ratio=0.005
    )
