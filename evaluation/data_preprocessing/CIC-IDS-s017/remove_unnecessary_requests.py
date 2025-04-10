from scapy.all import *
from datetime import datetime, timezone, timedelta


"""
Script to filter out any request that has no IP, source and destination port
This is paramount to reduce the amount of requests and not loose any information for the evaluation.
Requests without these information cannot be assigned to the CSV labels anyway, therefor they are just noise.
"""

# change these to the desired locations
input_pcap_file = "/mnt/d/master/Thursday-WorkingHours_corrected.pcap"
output_pcap_file = "/mnt/d/master/Thursday-WorkingHours_newly_corrected_ip_and_port_only.pcap"


print(output_pcap_file)
counter = 0
packets = 0
with PcapWriter(output_pcap_file, append=False) as pcap_writer:
    with PcapReader(input_pcap_file) as pcap_reader:
        for pkt in pcap_reader:
            if counter % 100000 == 0 and counter != 0:
                print(f"processed {counter} lines")
            if IP in pkt and hasattr(pkt, 'time') and hasattr(pkt, "sport") and hasattr(pkt, "dport"):
                pcap_writer.write(pkt)
                packets += 1
                if packets % 10000 == 0 and packets > 0:
                    print(f"processed {packets} packets and added them to the pcap")
            counter += 1
print(f"total count {counter}")
print(f"total added {packets}")
print(f"fraction {packets/counter}")