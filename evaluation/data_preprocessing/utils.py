from scapy.all import PcapReader, PcapWriter
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
    
class Precision(Enum):
    HOUR = "hour"
    MINUTE = "minute"
    SECOND = "second"
    MILISECOND = "milisecond" 
class Dataset():
    def __init__(self, sip_row, sport_row, dip_row, dport_row, labels_row, ts_row, base_dir_path, labels_path_glob, pcap_path_glob, combined_csv, combined_pcap, precision ):
        self.sip_row = sip_row
        self.sport_row= sport_row
        self.dip_row = dip_row
        self.dport_row = dport_row
        self.labels_row = labels_row
        self.ts_row = ts_row
        self.base_dir = base_dir_path
        self.labels_path = labels_path_glob
        # Output paths
        self.combined_csv = combined_csv
        self.combined_pcap = combined_pcap

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
        try:
            timestamp = datetime.fromtimestamp(row[self.ts_row])
        except:
            timestamp = parser.parse(row[self.ts_row], dayfirst=False).replace(tzinfo=None)
        timestamp = normalize_timestamp(timestamp, self.precision).strip()
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

    def get_keys_with_tolerance(self, key, precision, tolerance = 10):
        timestamp = parser.parse(key[0], dayfirst=False).replace(tzinfo=None)
        # for ms and s get a 1 sec tolerance
        if precision == Precision.MILISECOND.value or precision == Precision.SECOND.value:
            timestamp = timestamp.replace(microsecond=0)
            timestamps_with_tolerance = [timestamp + timedelta(seconds=offset) for offset in range(-tolerance, tolerance+1)]
        # otherwise get a 1 min. tolerance
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
                label = row[self.labels_row]
                if "benign" in label.casefold():
                    if target_benign >= benign:
                        csv_records[key] = True
                        csv_entries_list.append(row)
                        benign += 1
                else:
                    if target_malicious >= malicious:
                        csv_records[key] = True
                        csv_entries_list.append(row)
                        malicious += 1
                if target_malicious == malicious and target_benign == benign:
                    break
        print("last timestamp: ")
        print(key[0])
        return csv_records, csv_entries_list




    def sample_pcap_and_filter_csv_from_combined(self, output_pcap, output_csv, sample_ratio=0.05, packet_buffer=5):
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
        pcap_length = get_length_of_pcap(self.combined_pcap)
        sample_size = int(sample_ratio * pcap_length)
        # divide 1 by the ratio to get the absolute number of steps to take until a new sample is taken
        # * buffer + 1 is to sample around this modulo seleceted packet for bg traffic and special attack types which need more sample sizes
        # therefore we need to reduce the ammount of total modulo steps which is why sample steps needs to be bigger
        sample_steps = round((1 / sample_ratio) * (packet_buffer + 1))
        print(f"Pcap got {pcap_length} packets")
        print(f"Sampling {sample_size} from {self.combined_pcap}...")
        samples = []
        with PcapWriter(output_pcap, append=False) as pcap_writer:
            with PcapReader(self.combined_pcap) as reader:
                counter = 0
                for i, pkt in enumerate(reader):
                    # to not only sample only the beginngin of the file but rather all parts use the modulo
                    if i % sample_steps == 0:
                        counter = packet_buffer
                    # if modulo step is reached, sample the fllowing packets specified using the buffer
                    if counter > 0:
                        samples.append(pkt)
                        pcap_writer.write(pkt)
                        counter -= 1
                    # reset the counter again
                    else:
                        counter = 0
        print(f"Extracted {len(samples)} packets.")

        print(f"Loading CSV {self.combined_csv}...")
        csv_records = self.transform_csv_to_dict(self.combined_csv)

        print("Filtering CSV...")
        matches = {}
        for pkt in tqdm(samples, total=len(samples), desc="Sampling process"):
            match = self.get_packet_matches_of_csv(pkt, csv_records, self.precision)
            if match:
                matches[match] = True

        if matches:
            matching_rows = 0
            with open(output_csv, "w") as sampled_csv:
                writer = csv.writer(sampled_csv)
                with open(self.combined_csv, "r") as input_csv:
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




    def sample_subset_of_combined_files(self, output_pcap_file, output_csv_file, ratio=0.01):
        """
            Method to generate one pcap and csv file from all the dataset files. 
            A ratio can be given to reduce the amount of requests. 
            This was used to sample a given percentage from files in the dataset for slips.
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
        if all_ts_contain(timestamps,Precision.MILISECOND.value):
            if ts_have_different_values(timestamps, Precision.MILISECOND.value):
                return Precision.MILISECOND.value
        if all_ts_contain(timestamps,Precision.SECOND.value):
            if ts_have_different_values(timestamps, Precision.SECOND.value):
                return Precision.SECOND.value        
        if all_ts_contain(timestamps,Precision.MINUTE.value):
            if ts_have_different_values(timestamps, Precision.MINUTE.value):
                return Precision.MINUTE.value        
        else:
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
                if self.get_packet_matches_of_csv(pkt=packet, csv_records=csv_records, precision=self.precision) == None:
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
    return replaced_timestamp.strftime(timestamp_format)
    
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
