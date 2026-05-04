import os
from pathlib import Path
from scapy.all import PcapReader, PcapWriter
import os.path
import csv
from scapy.all import PcapReader
from tqdm import tqdm
from dateutil import parser 
from data_preprocessing.utils import Dataset, Precision, csv_row_is_empty
from data_preprocessing.sample_dataset_comparison import generate_sampling_comparison
from datetime import timedelta, timezone, datetime
import time

class CTU(Dataset):

    def plot_sampled_dataset_comparison(
        self,
        original_csv,
        output_dir,
        *,
        sampled_csv=None,
        original_pcap=None,
        sampled_pcap=None,
        embedding_method="auto",
        max_points_per_source=1000,
        random_state=42,
    ):
        sampled_csv = sampled_csv or self.combined_csv
        sampled_pcap = sampled_pcap or self.combined_pcap
        output_dir = Path(output_dir)
        return generate_sampling_comparison(
            self,
            original_csv=str(original_csv),
            sampled_csv=str(sampled_csv),
            output_dir=str(output_dir),
            dataset_name="ctu_13",
            original_pcap=str(original_pcap) if original_pcap is not None else None,
            sampled_pcap=str(sampled_pcap) if sampled_pcap is not None else None,
            embedding_method=embedding_method,
            max_points_per_source=max_points_per_source,
            random_state=random_state,
        )



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
                        if csv_row_is_empty(row) or self.csv_row_contains_invalid_information(row):
                            continue
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
        
        orig_time = parser.parse(row[0], dayfirst=False).replace(tzinfo=None) 
        start_time = orig_time + timedelta(hours=-2)
        start_time_human_readable = start_time.strftime(self.human_readable_timestamp_format)
        corrected_row[self.ts_row] = start_time_human_readable 
        # print(f"orig time: {orig_time} - start_time = {start_time} corrected time {start_time_human_readable}")      
        
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
                        #corrected_pkt = self.correct_pcap_pkt(pkt, timedelta(hours=2))
                        writer.write(pkt)
        print(f"Combined PCAP written to {self.combined_pcap}")



    def correct_pcap_pkt(self, pkt):
        
        def adjust_time_offset(pkt_time):
            time_offset = timedelta(hours=2)
            adjusted_time = pkt_time + time_offset
            return adjusted_time.strftime(self.human_readable_timestamp_format)

        corrected_pkt = pkt
        pkt_time = datetime.fromtimestamp(float(pkt.time), tz=timezone.utc).replace(tzinfo=None)
        adjusted_time_str = adjust_time_offset(pkt_time)
        parsed_datetime = datetime.strptime(adjusted_time_str, self.human_readable_timestamp_format).replace(tzinfo=timezone.utc)
        
        unix_timestamp = parsed_datetime.timestamp()
        corrected_pkt.time = unix_timestamp
        # print(f"original: {pkt_time} - updated: {parsed_datetime} - updated from ts: {test}")
        return corrected_pkt



# problem: not enough unique values 
# solutoin: sample malicoius and then benign using modulo!




    def sample_from_csv_with_target_malicious_and_random_benign(self, csv_file, target_benign, target_malicious, packet_buffer):
        """
            sample a subset of requests from a csv file. The target values ofr benign and malicious requests
            determine how many requests are sampled.
        """
        csv_records = {}
        csv_entries_list =[]
        total_rows_in_csv = 0
        benign = malicious = 0
        with open(csv_file, 'r') as input_csv:
            reader = csv.reader(input_csv)
            header = next(reader)  # Save the header row   
            csv_entries_list.append(header)
            # get malicious requests
            for row in reader:
                total_rows_in_csv += 1
                key = self.get_key_from_csv_row(row=row)             
                label = str(row[self.labels_row]).strip()
                if "benign" not in label.casefold():
                    if malicious < target_malicious:
                        csv_records[key] = True
                        csv_entries_list.append(row)
                        malicious += 1
                    else: 
                        print(f"sampled enough malicious - {malicious} rows")
                        break
            # then iterate over benign and get the using modulo
            sample_steps = int(total_rows_in_csv / (target_benign * packet_buffer))
        
            for i, row in enumerate(reader):
                key = self.get_key_from_csv_row(row=row)             
                label = str(row[self.labels_row]).strip()
                if i % sample_steps == 0:
                    counter = packet_buffer
                # if modulo step is reached, sample the fllowing packets specified using the buffer
                if counter > 0:
                    if "benign" in label.casefold():              
                        if benign < target_benign:
                            csv_records[key] = True
                            csv_entries_list.append(row)
                            benign += 1
                            counter -= 1
                        else: 
                            print(f"sampled enough benign - {benign} rows")   
                            break  
                else:
                    counter = 0                
        print(f"Sampled {benign} benign - {malicious} malicious - wanted: {target_benign} benign abd {target_malicious} malicious")
        return csv_records, csv_entries_list




    def sample_ctu_special_from_combined_csv_first(self, output_csv_file, output_pcap_file, malicious_ratio=0.02, benign_factor = 5, packet_buffer=3):
        """
        CTU dataset has only a small size of malicious requests, therefore it is not guaranteed that using modulo any malicious request is selected.
        Therefore, the csv needs to be sampled first and then the pcap which again will need to sample around each request using a buffer in order to 
        have background traffic and to be able to reflect various attack types which use more than one request. 
        """
        print(f"filenames {output_pcap_file}")
        print(f"filenames {output_csv_file}")
        start = time.time()
        benign, malicious = self.get_benign_malicious_counts(self.combined_csv)
        target_malicious = int(malicious*malicious_ratio)
        # use a fixed factor size for benign requests as otherwise too many requests would have been benign
        # as it is to be expected that most buffered packets are benign or bg traffic, the real number will be between
        # target_benign and target_benign * packet_buffer
        target_benign = target_malicious * benign_factor
        print(f"overall values: benign {benign}, malicious {malicious}")
        print(f"Target values: benign {target_benign}, malicious {target_malicious}")
        csv_records, csv_rows = self.sample_from_csv_with_target_malicious_and_random_benign(self.combined_csv, target_benign, target_malicious, packet_buffer )
        print(f"finished iteration and writing over CSV's after {time.time() - start} seconds")
        print("Now sampling from the pcap")
        with open(output_csv_file, "w") as f:
            writer = csv.writer(f)
            for row in csv_rows:
                writer.writerow(row)
        filtered_packets = 0
        counter = 0
        with PcapWriter(output_pcap_file, append=False) as pcap_writer:
            with PcapReader(self.combined_pcap) as pcap_reader:
                for packet in pcap_reader:
                    if counter % 1000000 == 0 and counter != 0:
                        print(f"processed {counter} lines")
                        print(f"currently filtered {filtered_packets} packets")
                        print(f"took {time.time() - start} seconds until now")
                    if self.get_packet_matches_of_csv(pkt=packet, csv_records=csv_records, precision=self.precision):
                        pcap_writer.write(packet)
                        filtered_packets += 1
                    counter += 1     
        print(f"currently filtered {filtered_packets} packets")

        
        
if __name__ == "__main__":
    original_combined_csv = os.getenv(
        "BICEP_CTU_13_ORIGINAL_CSV",
        "/mnt/hdd/Datasets/CTU-13/combined.csv",
    )
    original_combined_pcap = os.getenv(
        "BICEP_CTU_13_ORIGINAL_PCAP",
        "/mnt/hdd/Datasets/CTU-13/combined.pcap",
    )
    sampled_csv = "/mnt/hdd/Datasets/CTU-13/flow_based_sampling_timestamp_aware_reverse_key_overnight_bigger_last_try_100mb.csv"
    sampled_pcap = "/mnt/hdd/Datasets/CTU-13/flow_based_sampling_timestamp_aware_reverse_key_overnight_bigger_last_try_100mb.pcap"
    comparison_output_dir = os.getenv(
        "BICEP_CTU_13_PLOTS_DIR",
        "./data_preprocessing/ctu_13/plots_reduced",
    )

    ctu = CTU(
        sip_row=3,
        sport_row=4,
        dip_row=6,
        dport_row=7,
        protocol_row=2,
        labels_row=-1,
        ts_row=0,
        flow_duration_row=1,
        flow_duration_unit="seconds",
        base_dir_path="/mnt/hdd/Datasets/CTU-13/",
        labels_path_glob= ["*/*.binetflow"],
        pcap_path_glob=["*/*.pcap"],
        combined_csv=sampled_csv,
        combined_pcap=sampled_pcap ,
        precision=Precision.MILISECOND.value,
        sampled_csv=sampled_csv,
        sampled_pcap=sampled_pcap,
    )

    # ctu.convert_binetflow_to_csv_and_combine()
    # ctu.combine_pcaps()
    # can be used bot does not lookup reverse keys for flows.
    # ctu.sample_subset_of_combined_files(
    #     output_csv_file="/mnt/hdd/Datasets/CTU-13/sampled-ratio-0point5pc.csv",
    #     output_pcap_file="/mnt/hdd/Datasets/CTU-13/sampled-ratio-0point5pc.pcap",
    #     ratio=0.005
    # )
    # ctu.write_class_ratios_from_combined_csv_to_file("./data_preprocessing/ctu_13/ratio_reduced.txt")
    # ctu.write_noise_ratios_from_combined_pcap_to_file("./data_preprocessing/ctu_13/noise_ratio_reduced.txt")
    
    ctu.sample_from_csv_and_include_pcap_flow_based(
       output_csv="/mnt/hdd/Datasets/CTU-13/flow_based_sampling_timestamp_aware_reverse_key_overnight_bigger_last_try_100mb.csv",
       output_pcap="/mnt/hdd/Datasets/CTU-13/flow_based_sampling_timestamp_aware_reverse_key_overnight_bigger_last_try_100mb.pcap",
        sample_ratio_benign    = 0.00065,
        sample_ratio_malicious = 0.03,
        denoise=False

)

    ctu.validate_sampled_data()
    if Path(original_combined_csv).exists() and Path(original_combined_pcap).exists():
        ctu.plot_sampled_dataset_comparison(
            original_csv=ctu.combined_csv,
            original_pcap=ctu.combined_pcap,
            sampled_csv=ctu.sampled_csv,
            sampled_pcap=ctu.sampled_pcap,
            output_dir=comparison_output_dir,
        )
    else:
        print("Skipping sampled-vs-original comparison plots because the original CTU-13 files were not found.")
