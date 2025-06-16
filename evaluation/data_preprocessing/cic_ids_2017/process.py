import csv
from scapy.all import *
from data_preprocessing.utils import Dataset, Precision, csv_row_is_empty
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
from dateutil import parser

class CICIDS(Dataset):

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
    cicids = CICIDS(
        sip_row=1,
        sport_row=2,
        dip_row=3,
        dport_row=4,
        labels_row=-1,
        ts_row=6,
        base_dir_path="/mnt/hdd/Datasets/CIC-IDS-2017/",
        labels_path_glob= ["default-labels-files/*.csv"],
        pcap_path_glob=["default_pcaps/*.pcap"],
        combined_csv="/mnt/hdd/Datasets/CIC-IDS-2017/flow_based_sampling_timestamp_aware_reverse_key_overnight_bigger.csv",
        combined_pcap="/mnt/hdd/Datasets/CIC-IDS-2017/flow_based_sampling_timestamp_aware_reverse_key_overnight_bigger.pcap",
        precision=Precision.MINUTE.value
    )

    #cicids.combine_csv()
    # cicids.combine_pcaps()
    # cicids.sample_subset_of_combined_files(
    #     output_csv_file= "/mnt/hdd/Datasets/CIC-IDS-2017/sampled-ratio-0point5pc.csv",
    #     output_pcap_file="/mnt/hdd/Datasets/CIC-IDS-2017/sampled-ratio-0point5pc.pcap",
    #     ratio=0.005
    # )
    
#     cicids.sample_from_csv_and_include_pcap_flow_based(
#         output_csv="/mnt/hdd/Datasets/CIC-IDS-2017/flow_based_sampling_timestamp_aware_reverse_key_overnight_bigger.csv",
#         output_pcap= "/mnt/hdd/Datasets/CIC-IDS-2017/flow_based_sampling_timestamp_aware_reverse_key_overnight_bigger.pcap",
#         sample_ratio_benign    = 0.002,
#         sample_ratio_malicious = 0.01
# )

    cicids.write_class_ratios_from_combined_csv_to_file("./data_preprocessing/cic_ids_2017/ratio_reduced.txt")
    cicids.write_noise_ratios_from_combined_pcap_to_file("./data_preprocessing/cic_ids_2017/noise_ratio_reduced.txt")
