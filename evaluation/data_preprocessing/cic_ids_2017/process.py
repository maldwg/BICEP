import csv
from scapy.all import *
from data_preprocessing.utils import Dataset
from tqdm import tqdm
from datetime import datetime, timedelta
from dateutil import parser

class CICIDS(Dataset):

    def combine_csv(self):
        header_included = False
        print(f"Combining csvs to {self.combined_csv}")
        with open(self.combined_csv, "w") as output:
            writer = csv.writer(output)
            for c in self.labels_files:
                print(f"Now adding {c}")
                with open(c, "r") as input:
                    reader = csv.reader(input)
                    header = next(reader)
                    if not header_included:
                        writer.writerow(header)
                        header_included = True
                    for row in reader:
                        corrected_row = row # self.correct_csv_row(row)
                        writer.writerow(corrected_row)
        print("Sucessfully finished combining the csvs")



    def combine_pcaps(self):
        print(f"Combining pcaps to {self.combined_pcap}")
        with PcapWriter(self.combined_pcap, append=True) as writer:
            for pcap in self.pcap_files:
                print(f"Now adding {pcap}")
                with PcapReader(pcap) as reader:
                    for pkt in tqdm(reader, desc=f"Processing of {pcap}"):
                        corrected_pkt = pkt # self.correct_pcap_pkt(pkt)
                        writer.write(corrected_pkt)




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
        corrected_row[6] = csv_time.isoformat()             
        return corrected_row


    def correct_pcap_pkt(self, pkt):
        time_offset = timedelta(hours=-3)
        def adjust_time_offset(pkt_time):
            adjusted_time = pkt_time + time_offset
            return adjusted_time.strftime(format)

        corrected_pkt = pkt
        pkt_time = datetime.fromtimestamp(float(pkt.time))
        adjusted_time_str = adjust_time_offset(pkt_time)
        parsed_datetime = datetime.strptime(adjusted_time_str, self.human_readable_timestamp_format)
        unix_timestamp = parsed_datetime.timestamp()
        corrected_pkt.time = unix_timestamp
        return corrected_pkt

if __name__ == "__main__":
    cicids = CICIDS(
        sip_row=1,
        sport_row=2,
        dip_row=3,
        dport_row=4,
        labels_row=-1,
        ts_row=6,
        base_dir_path="/mnt/hdd/Datasets/CIC-IDS-2017/",
        labels_path_glob=["*corrected.csv"],
        pcap_path_glob=["*corrected.pcap"],
        combined_csv="/mnt/hdd/Datasets/CIC-IDS-2017/combined.csv",
        combined_pcap="/mnt/hdd/Datasets/CIC-IDS-2017/combined.pcap"
    )

    # cicids.combine_csv()
    # cicids.combine_pcaps()
    # cicids.sample_subset_of_combined_files(
    #     output_csv_file="/mnt/hdd/Datasets/CIC-IDS-2017/sampled-ratio-1pc.csv",
    #     output_pcap_file="/mnt/hdd/Datasets/CIC-IDS-2017/sampled-ratio-1pc.csv",
    #     ratio=0.01
    # )
