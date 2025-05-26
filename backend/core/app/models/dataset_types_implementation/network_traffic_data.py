"""
This implementation enables a user to use the following structure as datasets for the IDS:
    1. A pcap file with all the requests. May include background traffic, noise, etc.
    2. A CSV file with:
        a) information on the Source and Destintation (IP and Port), 
        b) timestamp in human readable form
        c) a label which contains the keyword "benign" or "malicious"
"""
from app.logger import LOGGER
import csv
from app.utils import HourPrecision, MinutePrecision, SecondPrecision, MilisecondPrecision, get_precision_by_name, normalize_and_parse_alert_timestamp, extract_ts_srcip_srcport_dstip_dstport_from_alert, get_item_counts_of_dict, Precision
from app.bicep_utils.models.ids_base import Alert
from datetime import timedelta
from dateutil import parser
import random

def network_traffic_data_calculate_precision(labels_file_path):

    def get_header_and_sample_rows_from_csv(labels_file_path):
        with open(labels_file_path, "r", encoding="utf-8") as input:
            reader = csv.reader(input)
            header = next(reader)
            all_rows = list(reader)
        return header, random.sample(all_rows, 5)

    def parse_timestamp(timestamp):
        return parser.parse(timestamp, dayfirst=False).replace(tzinfo=None)

    # TODO 1: maybe enough to look for 0 values ? unliekly that everywhere there will be the same sec, ms, min, etc. 
    header, random_rows = get_header_and_sample_rows_from_csv(labels_file_path)
    _, timestamp_col_id, _, _, _, _ = _get_column_ids(header)
    timestamps = [ parse_timestamp(row[timestamp_col_id]) for row in random_rows]
    if not all(ts.microsecond == 0 for ts in timestamps):
        return MilisecondPrecision()
    if not all(ts.second == 0 for ts in timestamps):
        return SecondPrecision()       
    if not all(ts.minute == 0 for ts in timestamps):
        return MinutePrecision()      
    else:
        return HourPrecision()

def network_traffic_data_get_benign_and_malicious_counts_of_labels_file(labels_file_path) -> tuple[int, int]:
    """
    Method to calculate how many entries of the dataset contain benign and malicious data

    Args:
        labels_file_text_stream: The text stream of the labels file containing the classes
    
    Returns:
        benign_count (int): Amount of benign data points
        malicious_count (int): Amount of malicious data points

    """
    benign_count = 0
    malicious_count = 0
    header = True
    with open(labels_file_path, "r", encoding="utf-8") as input_csv:
        reader = csv.reader(input_csv)
        for row in reader:
            if header:
                header = False
                continue
            # Convert each cell in the row to lowercase and check for "benign"
            if any("benign" in cell.lower() for cell in row):
                benign_count += 1
            else:
                malicious_count += 1
    return benign_count, malicious_count


def network_traffic_data_get_positives_and_negatives_from_dataset(dataset, alerts: list[Alert]) -> tuple[int, int, int, int, int, int]:
    """
    Method that receives an alert list as input and compares it to the dataset. 

    Args:
        dataset (Dataset): A Dataset object to access the labels and data files
        alerts (list[Alert]): The alert list yielded by an IDS or Ensemble

    Returns: 
        TP (int): Amount of True Positives found
        FP (int):  Amount of False Positives found
        TN (int):  Amount of True Negatives found
        FN (int):   Amount of False Negatives found
        UNASSIGNED_ALERTS (int): Amount of alerts that could not be assigned to one of the rows in the labels file. If 2 Alerts point to the same row in the labels file, 1 of them will remain unassigned
        TOTAL_ALERTS (int): How many alerts were yielded ?
    """

    TP = TN = FN = FP = 0
    precision = get_precision_by_name(dataset.timestamp_precision)
    # save in a dict for performance reasons 
    alerts_dict = {}
    for alert in alerts:
        timestamp, source_ip, source_port, destination_ip, destination_port = extract_ts_srcip_srcport_dstip_dstport_from_alert(alert, precision)
        key = (timestamp,source_ip,source_port,destination_ip,destination_port)
        # for each key, save all alerts from the ids that fall into that key (multiple possible, e.g. if ids says 1 request violates 2 rules)
        alerts_dict[key] = alerts_dict.get(key, []) + [alert]
    TOTAL_ALERTS = get_item_counts_of_dict(alerts_dict)
    
    # iterate over ground truth csv and compare each entry to the alerts
    with open(dataset.labels_file_path, 'r') as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)
        # Get column dynamically from header
        label_col_id, timestamp_col_id, src_ip_col_id, src_port_col_id, dst_ip_col_id, dst_port_col_id = _get_column_ids(header)
        direct_counter = 0
        tolerance_counter = 0
        reverse_tolerance_counter = 0
        else_counter = 0
        reverse_direct_counter = 0
        for row in reader:
            row_timestamp = normalize_and_parse_alert_timestamp(row[timestamp_col_id], precision)
            row_source_ip = row[src_ip_col_id].strip()
            row_source_port = row[src_port_col_id].strip()
            row_destination_ip = row[dst_ip_col_id].strip()
            row_destination_port = row[dst_port_col_id].strip()
            base_key = (row_timestamp,row_source_ip,row_source_port,row_destination_ip,row_destination_port)
            reverse_key = _get_reverse_key(base_key)
            # try to find key directly from csv values (ibcluding reverse value) == 0. level match
            if base_key in alerts_dict:
                _remove_key_from_dict(base_key, alerts_dict)
                if _is_request_benign(row[label_col_id]):
                    FP += 1
                else:
                    TP += 1
                direct_counter += 1
                continue
            # find plain reverse key == 1st level match
            elif reverse_key in alerts_dict:
                _remove_key_from_dict(reverse_key, alerts_dict)
                if _is_request_benign(row[label_col_id]):
                    FP += 1
                else:
                    TP += 1
                reverse_direct_counter += 1                 
                continue                
            else:
                key_found = False
                keys_with_tolerance = _get_keys_with_tolerance(key=base_key, precision = precision)
                # try to find key for csv row + time buffer in alerts == 2. level match
                for key in keys_with_tolerance:
                    if key in alerts_dict:
                        _remove_key_from_dict(key, alerts_dict)
                        if _is_request_benign(row[label_col_id]):
                            FP += 1
                        else:
                            TP += 1
                        key_found = True
                        tolerance_counter += 1
                        break
                if not key_found:
                    # try to find csv row reverse key with tolerance == 3. level match
                    reverse_keys_with_tolerance = _get_keys_with_tolerance(key=reverse_key, precision = precision)
                    for r_key in reverse_keys_with_tolerance:
                        if r_key in alerts_dict:
                            _remove_key_from_dict(r_key, alerts_dict)
                            if _is_request_benign(row[label_col_id]):
                                FP += 1
                            else:
                                TP += 1
                            key_found = True
                            reverse_tolerance_counter += 1
                            break    
                # if no reversekey and normal key even with tolerance found == 4th level match                        
                if not key_found:
                    else_counter += 1
                    if _is_request_benign(row[label_col_id]):
                        TN += 1
                    else:
                        FN += 1
    total_matches = direct_counter + tolerance_counter + reverse_tolerance_counter + else_counter
    print(f"Direct matches: {direct_counter}, reverse direct matches {reverse_direct_counter},tolerance matches: {tolerance_counter}, reverse_matches {reverse_tolerance_counter}, else matches: {else_counter}")
    # amount of alerts that could not be assigned to a label, for isntance if multiple alerts exist for 1 label
    UNASSIGNED_ALERTS = get_item_counts_of_dict(alerts_dict)
    LOGGER.debug(f"TP {TP}, FP {FP}, TN {TN}, FN {FN}, Unassigned: {UNASSIGNED_ALERTS} of {TOTAL_ALERTS}")

    return TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS



## helper methods
def _remove_key_from_dict(key, dict):
    dict[key].pop(0)
    if dict[key] == []: 
        del dict[key]    

def _get_reverse_key(key):
    ts, src_ip, src_port, dst_ip, dst_port = key
    return (ts, dst_ip, dst_port, src_ip, src_port)

def _is_request_benign(cell: str) -> bool:
    if "benign" == str(cell).lower().strip():
        return True
    return False

def _get_index(lst: list, search_list: list[str]) -> int:
    """
    Method to lookup a list index based on a search list
    Args: 
        lst (list): The list to search 
        search_list (list[str]): Contains keywords or phrases to look for in lst
    
    Returns: 
        index (int): The first index in the list that contains any of the search_list entries
    """
    for index, element in enumerate(lst):
            # Compare the lowercase versions of the strings
            element = str(element).strip().casefold()
            for search in search_list:
                if str(element).casefold() == search.casefold():
                    return index
    raise KeyError(f"list {lst} does not contain any of these keywords: {search_list}")

def _get_column_ids(header: list) -> tuple[int, int, int, int ,int ,int]:
    """
    Looks in the header row of a labels file for the necessary column indexes to construct Alerts
    Args: 
        header (list): A list containing all column names
    Returns: 
        label_col_id (int): The index containing the label for an entry
        timestamp_col_id (int): The index containing the timestamp
        src_ip_col_id (int): The index containing the source ip
        src_port_col_id (int): Index containing the source port
        dst_ip_col_id (int): Index containing th destination ip
        dst_port_col_id (int): Index containing the destination port
    """
    label_col_id = _get_index(header, ["Label", "Class"])
    timestamp_col_id = _get_index(header, ["Time", "Timestamp", "StartTime", "Stime"])
    src_ip_col_id = _get_index(header, ["Source", "Source-IP", "Source_IP", "Source IP", "Src", "Src_IP", "Src-IP", "Src_IP", "Src IP", "SrcAddr", "SrcIP"])
    src_port_col_id = _get_index(header, ["Source Port", "Source-Port", "Source_Port", "Src_Port", "Src-Port", "Src Port", "Sport"])
    dst_ip_col_id = _get_index(header, ["Destination", "Destination-IP", "Destination_IP", "Destination IP", "Dst", "Dst_IP", "Dst-IP", "Dst IP", "DstAddr", "DstIP"])
    dst_port_col_id = _get_index(header, ["Destination Port", "Destination-Port", "Destination_Port", "Dst_Port", "Dst-Port", "Dst Port", "Dport", "Dsport"])
    return label_col_id,timestamp_col_id, src_ip_col_id, src_port_col_id, dst_ip_col_id, dst_port_col_id

def _get_keys_with_tolerance(key, precision: Precision, tolerance_unit = 10):
    timestamp = parser.parse(key[0], dayfirst=False).replace(tzinfo=None)
    timestamps_with_tolerance = precision.calculate_timestamps_with_tolerance(timestamp, tolerance_unit=tolerance_unit)
    keys = []
    for ts in timestamps_with_tolerance:
        new_key = list(key)  
        new_key[0] = ts.replace(tzinfo=None).strftime(precision.timestamp_format)
        keys.append(tuple(new_key))
    return keys




