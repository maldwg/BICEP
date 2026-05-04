import csv
import os
from pathlib import Path
from scapy.all import *
from data_preprocessing.utils import Dataset, Precision, csv_row_is_empty
from data_preprocessing.sample_dataset_comparison import generate_sampling_comparison
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
from dateutil import parser

class CICIDS(Dataset):

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
            dataset_name="cic_ids_2017",
            original_pcap=str(original_pcap) if original_pcap is not None else None,
            sampled_pcap=str(sampled_pcap) if sampled_pcap is not None else None,
            embedding_method=embedding_method,
            max_points_per_source=max_points_per_source,
            random_state=random_state,
        )

    def combine_csv(self):
        header_included = False
        print(f"Combining csvs to {self.combined_csv}")
        with open(self.combined_csv, "w") as output:
            writer = csv.writer(output)
            for c in self.labels_files:
                print(f"Now adding {c}")
                with open(c, "r",  encoding="utf-8", errors="replace") as input:
                    reader = csv.reader(input)
                    header = next(reader)
                    if not header_included:
                        writer.writerow(header)
                        header_included = True
                    for row in reader:
                        if csv_row_is_empty(row) or self.csv_row_contains_invalid_information(row):
                            continue
                        try:
                            corrected_row = self.correct_csv_row(row)
                            writer.writerow(corrected_row)
                        except:
                            pass
        print("Sucessfully finished combining the csvs")



    def combine_pcaps(self):
        print(f"Combining pcaps to {self.combined_pcap}")
        #counter = 0
        with PcapWriter(self.combined_pcap, append=True) as writer:
            for pcap in self.pcap_files:
                print(f"Now adding {pcap}")
                with PcapReader(pcap) as reader:
                    for pkt in tqdm(reader, desc=f"Processing of {pcap}"):
                        # correct packets only when using the raw files from the dataset. Mine were already preprocessed
                        # adjust to -3 offfset for non processed files
                        # corrected_pkt = self.correct_pcap_pkt(pkt, time_offset=timedelta(hours=0))
                        writer.write(pkt)
                        # counter += 1
                        # if counter >0 and counter % 100 == 0:
                        #     break



    # theoretically better to only correct the csv but 
    def correct_csv_row(self, row):
        def adjust_time_to_24_hour_format(csv_time):
            hour = csv_time.hour
            if 1 <= hour <= 7:
                csv_time = csv_time + timedelta(hours=12)
            return csv_time

        corrected_row = row
        csv_time_cell = row[6]  
        csv_time = parser.parse(csv_time_cell,dayfirst=True).replace(tzinfo=None)
        csv_time = adjust_time_to_24_hour_format(csv_time)
        csv_time = csv_time + timedelta(hours=3)
        # use strftime and the timeformat here, otherwise second values can remain in some files!
        corrected_row[6] = csv_time.strftime("%Y-%m-%d %H:%M")             
        label = str(row[self.labels_row]).casefold()
        if label == "benign":
            corrected_row[self.labels_row] = label
        else:
            corrected_row[self.labels_row] = "malicious"
        
        return corrected_row

if __name__ == "__main__":
    original_combined_csv = os.getenv(
        "BICEP_CIC_IDS_2017_ORIGINAL_CSV",
        "/mnt/hdd/Datasets/CIC-IDS-2017/baseline/combined.csv",
    )
    original_combined_pcap = os.getenv(
        "BICEP_CIC_IDS_2017_ORIGINAL_PCAP",
        "/mnt/hdd/Datasets/CIC-IDS-2017/baseline/combined.pcap",
    )
    sampled_csv = "/mnt/hdd/Datasets/CIC-IDS-2017/truly_flow_based.csv"
    sampled_pcap = "/mnt/hdd/Datasets/CIC-IDS-2017/truly_flow_based.pcap"
    comparison_output_dir = os.getenv(
        "BICEP_CIC_IDS_2017_PLOTS_DIR",
        "./data_preprocessing/cic_ids_2017/plots_reduced",
    )

    cicids = CICIDS(
        sip_row=1,
        sport_row=2,
        dip_row=3,
        dport_row=4,
        protocol_row=5,
        labels_row=-1,
        ts_row=6,
        flow_duration_row=7,
        flow_duration_unit="microseconds",
        base_dir_path="/mnt/hdd/Datasets/CIC-IDS-2017/",
        labels_path_glob= ["default-labels-files/*.csv"],
        pcap_path_glob=["default_pcaps/*.pcap"],
        combined_csv=original_combined_csv,
        combined_pcap=original_combined_pcap,
        sampled_csv=sampled_csv,
        sampled_pcap=sampled_pcap,
        precision=Precision.MINUTE.value
    )
    
    #cicids.combine_csv()
    # cicids.combine_pcaps()
    # cicids.sample_subset_of_combined_files(
    #     output_csv_file= "/mnt/hdd/Datasets/CIC-IDS-2017/sampled-ratio-0point5pc.csv",
    #     output_pcap_file="/mnt/hdd/Datasets/CIC-IDS-2017/sampled-ratio-0point5pc.pcap",
    #     ratio=0.005
    # )
    
    cicids.sample_from_csv_and_include_pcap_flow_based(
        output_csv=sampled_csv,
        output_pcap=sampled_pcap,
        sample_ratio_benign    = 0.002,
        sample_ratio_malicious = 0.01,
        # denoise normally but dont denoise to maintain noisy structure in samples!
        denoise=False
)

    # cicids.write_class_ratios_from_combined_csv_to_file("./data_preprocessing/cic_ids_2017/ratio_reduced.txt")
    # cicids.write_noise_ratios_from_combined_pcap_to_file("./data_preprocessing/cic_ids_2017/noise_ratio_reduced.txt")
    
    cicids.validate_sampled_data() 
    if Path(sampled_csv).exists() and Path(sampled_pcap).exists():
        cicids.plot_sampled_dataset_comparison(
            original_csv=cicids.combined_csv,
            original_pcap=cicids.combined_pcap,
            sampled_csv=cicids.sampled_csv,
            sampled_pcap=cicids.sampled_pcap,
            output_dir=comparison_output_dir,
        )
    else:
        print("Skipping sampled-vs-original comparison plots because the original CIC-IDS-2017 files were not found.")
