from scapy.all import *
import csv
from datetime import datetime, timezone
import time
from dateutil import parser


def assemble_slips(pcap_files, csv_files, output_pcap_file, output_csv_file, ratio=0.0025):
    """
        Method to generate one pcap and csv file from all the dataset files. 
        A ratio can be given to reduce the amount of requests. 
        This was used to sample a given percentage from files in the dataset for slips.
    """
    print(f"filenames {output_pcap_file}")
    print(f"filenames {output_csv_file}")
    start = time.time()
    # Read the CSV file
    header_included = False
    csv_entries = 0
    csv_records = {}
    with open(output_csv_file, 'w') as output_csv:
        writer = csv.writer(output_csv)
        for csv_file in csv_files:
            with open(csv_file, 'r') as input_csv:
                benign, malicious = get_benign_malicious_counts(csv_file)
                target_benign = int(benign*ratio)
                target_malicious = int(malicious*ratio)
                print(f"overall values: benign {benign}, malicious {malicious}")
                print(f"Target values: benign {target_benign}, malicious {target_malicious}")
                single_csv_records, csv_rows = sample_from_csv(csv_file, target_benign, target_malicious)
                csv_records.update(single_csv_records)
                if not header_included:
                    writer.writerow(csv_rows[0])
                    csv_rows.pop(0)
                    header_included = True
                for row in csv_rows:
                    writer.writerow(row)
                    csv_entries += 1
    print("now the pcap")
    print(f"finished iteration and writing over CSV's after {time.time() - start} seconds")

    filtered_packets = 0
    counter = 0
    pcap_counter = 0
    with PcapWriter(output_pcap_file, append=False) as pcap_writer:
        for pcap_file in pcap_files:
            pcap_counter += 1
            with PcapReader(pcap_file) as pcap_reader:
                for packet in pcap_reader:
                    if counter % 1000000 == 0 and counter != 0:
                        print(f"processed another 1000000 lines")
                        print(f"currently filtered {filtered_packets} packets")
                        print(f"took {time.time() - start} seconds until now")

                    if IP in packet and hasattr(packet, 'time'):
                        # Extract the source and destination IP and ports
                        src_ip = packet[IP].src
                        dest_ip = packet[IP].dst
                        src_port = str(packet.sport) if hasattr(packet, 'sport') else '0'
                        dest_port = str(packet.dport) if hasattr(packet, 'dport') else '0'
                        # Convert timestamp to the same format as in CSV
                        packet_time_float = float(packet.time)
                        packet_timestamp = datetime.fromtimestamp(packet_time_float, tz=timezone.utc).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M')

                        key = (packet_timestamp, src_ip, src_port, dest_ip, dest_port)
                        if key in csv_records:
                            pcap_writer.write(packet)
                            filtered_packets += 1
                            if filtered_packets % 10000 == 0 and filtered_packets != 0:
                                print(f"Wrote {filtered_packets} to the file already")
                    counter += 1
            print(f"Took {time.time() - start} seconds for the {pcap_counter}. pcap file")
    print(f"csv length: {csv_entries}, pcap length: {filtered_packets}, overall {counter} pcap requests")
    end = time.time()
    print(f"took {end-start} seconds to finish")


def cleanup_data(pcap_file, csv_file, output_pcap_file, output_csv_file=None, limit=None, malicious_min= None):
    """
    Method to take a CSV as input, populate a dict to hold information about each requests in the CSV.
    Then iterate through the respective pcap and sort out any request that cannot be assigned to the CSV file. 
    This reduces the pcap tremendously.
    """
    # Why this cleanup?
    # because too many nassignabel requests and mini sampling of data wont work this way. Also pcap holds 10 times the requests... 
    print(f"filenames {output_pcap_file} - limit {limit}")
    start = time.time()
    csv_records = {}
    rows = []
    # Read the CSV file
    counter = 0
    malicious_counter = 0
    with open(csv_file, 'r') as input_csv:
        reader = csv.reader(input_csv)
        header = next(reader)  # Save the header row
        rows.append(header)
        
        for row in reader:
            src_ip = row[1]
            src_port = str(row[2])
            dest_ip = row[3]
            dest_port = str(row[4])
            timestamp = parser.parse(row[6], dayfirst=False).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M')
            
            key = (timestamp, src_ip, src_port, dest_ip, dest_port)
            if malicious_min:
                label = row[-1]
                if "benign" in label.casefold():
                    if malicious_counter < malicious_min and malicious_min - malicious_counter + counter >= limit:
                        continue
                    else:
                        csv_records[key] = True
                        rows.append(row)
                        counter += 1
                else:
                    csv_records[key] = True
                    rows.append(row)
                    malicious_counter += 1
            else:
                csv_records[key] = True
                rows.append(row)
                counter += 1
            if limit:
                if counter + malicious_counter == limit:
                    break

    print(len(rows))
    if limit:
        print("writing csv file")
        with open(output_csv_file, 'w') as output_csv:
            writer = csv.writer(output_csv)
            writer.writerows(rows)
    rows_length = len(rows)
    rows = [] # reset to save memory
    print("now the pcap")

    filtered_packets = 0
    counter = 0
    with PcapWriter(output_pcap_file, append=False) as pcap_writer:
        with PcapReader(pcap_file) as pcap_reader:
            for packet in pcap_reader:
                if counter % 10000 == 0 and counter != 0:
                    print(f"processed another 10000 lines")
                    print(f"currently filtered {filtered_packets} packets")
                    print(f"took {time.time() - start} seconds until now")

                if IP in packet and hasattr(packet, 'time'):
                    # Extract the source and destination IP and ports
                    src_ip = packet[IP].src
                    dest_ip = packet[IP].dst
                    src_port = str(packet.sport) if hasattr(packet, 'sport') else '0'
                    dest_port = str(packet.dport) if hasattr(packet, 'dport') else '0'
                    # Convert timestamp to the same format as in CSV
                    packet_time_float = float(packet.time)
                    packet_timestamp = datetime.fromtimestamp(packet_time_float, tz=timezone.utc).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M')

                    key = (packet_timestamp, src_ip, src_port, dest_ip, dest_port)
                    if key in csv_records:
                        pcap_writer.write(packet)
                        filtered_packets += 1
                        if filtered_packets % 10000 == 0 and filtered_packets != 0:
                            print(f"Wrote {filtered_packets} to the file already")
                counter += 1
    print(f"csv length: {rows_length}, pcap length: {filtered_packets}, overall {counter} pcap requests")
    end = time.time()
    print(f"took {end-start} seconds to finish")


def sample_subset(csv_file, output_csv_file, pcap_file, output_pcap_file, ratio=0.25):
    """
        main method to sample a subset of a dataset day in the CIC-IDS dataset. 
        The ratio defines how many percent of the requests from the CSV are to be sampled.
        The pcap requests are sampled accordingly
    """
    print(f"subsetting for csv file {csv_file} and pcap {pcap_file}")
    start = time.time()
    benign, malicious = get_benign_malicious_counts(csv_file)
    target_benign = int(benign*ratio)
    target_malicious = int(malicious*ratio)
    print(f"overall values: benign {benign}, malicious {malicious}")
    print(f"Target values: benign {target_benign}, malicious {target_malicious}")
    csv_records, csv_rows = sample_from_csv(csv_file, target_benign, target_malicious)
    write_csv(csv_rows, output_csv_file)
    # save memory
    csv_rows = []
    write_requests_from_pcap(pcap_file, output_pcap_file, csv_records)

    end = time.time()
    print(f"took {end - start} seconds to finish")

def write_csv(csv_rows, output_csv_file):
    with open(output_csv_file, 'w') as output_csv:
        writer = csv.writer(output_csv)
        writer.writerows(csv_rows)

def write_requests_from_pcap(pcap_file, output_pcap_file,csv_records):
    """
        Method tha checks for each request in a pcap file, 
        if it occurs in the csv_records. If yes, write the request to a new file,
        if not, skip.
    """
    filtered_packets = 0
    counter = 0
    start = time.time()
    with PcapWriter(output_pcap_file, append=False) as pcap_writer:
        with PcapReader(pcap_file) as pcap_reader:
            for packet in pcap_reader:
                if counter % 10000 == 0 and counter != 0:
                    print(f"processed another 10000 lines")
                    print(f"currently filtered {filtered_packets} packets")
                    print(f"took {time.time() - start} seconds until now")

                if IP in packet and hasattr(packet, 'time'):
                    # Extract the source and destination IP and ports
                    src_ip = packet[IP].src
                    dest_ip = packet[IP].dst
                    src_port = str(packet.sport) if hasattr(packet, 'sport') else '0'
                    dest_port = str(packet.dport) if hasattr(packet, 'dport') else '0'
                    # Convert timestamp to the same format as in CSV
                    packet_time_float = float(packet.time)
                    packet_timestamp = datetime.fromtimestamp(packet_time_float, tz=timezone.utc).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M')

                    key = (packet_timestamp, src_ip, src_port, dest_ip, dest_port)
                    if key in csv_records:
                        pcap_writer.write(packet)
                        filtered_packets += 1
                        if filtered_packets % 10000 == 0 and filtered_packets != 0:
                            print(f"Wrote {filtered_packets} to the file already")
                counter += 1
    end = time.time()
    print(f"took {end-start} seconds to finish iterating over the pcap")




def sample_from_csv(csv_file, target_benign, target_malicious):
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
            src_ip = row[1]
            src_port = str(row[2])
            dest_ip = row[3]
            dest_port = str(row[4])
            timestamp = parser.parse(row[6], dayfirst=False).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M')
            key = (timestamp, src_ip, src_port, dest_ip, dest_port)
            label = row[-1]
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
    return csv_records, csv_entries_list



def get_benign_malicious_counts(csv_file):
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


# Paths to the files
# pcap_file = "/mnt/d/master/Wednesday-WorkingHours_corrected_csv_aligned.pcap"
# csv_file =  "/mnt/d/master/Wednesday-WorkingHours_newly_corrected.csv"
# output_pcap_file = "/mnt/d/master/Wednesday-WorkingHours_2point5.pcap"
# output_csv_file =  "/mnt/d/master/Wednesday-WorkingHours_2point5.csv"
# cleanup_data(pcap_file, csv_file, output_pcap_file)
# get_length_of_sampled_data(filtered_pcap_file, csv_file)
# sample_subset(csv_file=csv_file, output_csv_file=output_csv_file, pcap_file=pcap_file, output_pcap_file=output_pcap_file, ratio=0.025)



# Paths to the files
pcap_files = [
    "/mnt/d/master/Monday-WorkingHours_corrected_csv_aligned.pcap",
    "/mnt/d/master/Tuesday-WorkingHours_corrected_csv_aligned.pcap",
    "/mnt/d/master/Wednesday-WorkingHours_corrected_csv_aligned.pcap",
    "/mnt/d/master/Thursday-WorkingHours_corrected_csv_aligned.pcap",
    "/mnt/d/master/Friday-WorkingHours_corrected_csv_aligned.pcap",

]
csv_files =  [
    "/mnt/d/master/Monday-WorkingHours_newly_corrected.csv",
    "/mnt/d/master/Tuesday-WorkingHours_newly_corrected.csv",
    "/mnt/d/master/Wednesday-WorkingHours_newly_corrected.csv",
    "/mnt/d/master/Thursday-WorkingHours_newly_corrected.csv",
    "/mnt/d/master/Friday-WorkingHours_newly_corrected.csv",
]
output_pcap_file = "/mnt/d/master/All-WorkingHours_slips_1percent.pcap"
output_csv_file =  "/mnt/d/master/All-WorkingHours_slips_1percent.csv"
assemble_slips(pcap_files, csv_files, output_pcap_file, output_csv_file, ratio=0.01)