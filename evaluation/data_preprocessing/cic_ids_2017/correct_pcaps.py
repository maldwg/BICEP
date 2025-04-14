from scapy.all import *
from datetime import datetime, timezone, timedelta

"""
Script to adjust the timestamps in the pcap by removing the offset of 3 hours
"""

# change these as needed
input_pcap_file = "/mnt/d/master/Friday-WorkingHours.pcap"
output_pcap_file = "/mnt/d/master/Friday-WorkingHours_corrected.pcap"



format ="%d/%m/%Y %H:%M:%S"
time_offset = timedelta(hours=-3)
def adjust_time_offset(pkt_time):
    adjusted_time = pkt_time + time_offset
    return adjusted_time.strftime(format)

counter = 0
packets = [] 
with PcapWriter(output_pcap_file, append=False) as pcap_writer:
    with PcapReader(input_pcap_file) as pcap_reader:
        for pkt in pcap_reader:
            if counter % 100000 == 0 and counter != 0:
                print("processed another 100000 lines")
            pkt_time = datetime.fromtimestamp(float(pkt.time))
            adjusted_time_str = adjust_time_offset(pkt_time)
            parsed_datetime = datetime.strptime(adjusted_time_str, format)
            unix_timestamp = parsed_datetime.timestamp()
            pkt.time = unix_timestamp
            pcap_writer.write(pkt)
            counter += 1