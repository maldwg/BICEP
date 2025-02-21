from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship, Session
from ..database import Base
import sys
import asyncio
from ..bicep_utils.models.ids_base import Alert
from ..logger import LOGGER
import csv
from ..utils import normalize_and_parse_alert_timestamp, extract_ts_srcip_srcport_dstip_dstport_from_alert, get_item_counts_of_dict


class DatasetType(Base):
    __tablename__ = "dataset_type"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    description = Column(String(2048), nullable=False)
    function_prefix = Column(String(128), nullable= False)

    dataset = relationship('Dataset', back_populates="dataset_type")

    async def get_benign_and_malicious_counts(self, labels_file_text_stream):
        function_name = f"{self.function_prefix.lower()}_get_benign_and_malicious_counts_of_labels_file"
        module = sys.modules[__name__]
        func = getattr(module, function_name)
        return await asyncio.to_thread(func, labels_file_text_stream)

    async def get_positives_and_negatives_from_dataset(self, dataset, alerts: list[Alert]):
        function_name = f"{self.function_prefix.lower()}_get_positives_and_negatives_from_dataset"
        module = sys.modules[__name__]
        func = getattr(module, function_name)
        return await asyncio.to_thread(func, dataset, alerts)


#############################
### general db operations ###
#############################

def get_dataset_type_by_id(db: Session, id: int):
    return db.query(DatasetType).filter(DatasetType.id == id).first()

def get_all_dataset_types(db: Session):
    return db.query(DatasetType).all()

#################################################
### Methods for Network traffic dataset types ###
### which use pcaps and csv label files       ###
#################################################

def network_traffic_data_get_benign_and_malicious_counts_of_labels_file(labels_file_text_stream):
    benign_count = 0
    malicious_count = 0
    header = True
    with labels_file_text_stream as input_csv:
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


def network_traffic_data_get_positives_and_negatives_from_dataset(dataset, alerts: list[Alert]):
    #####################################################
    ###  helper methods to make code more expressive ####
    #####################################################
    def is_request_benign(cell):
        if "benign" == str(cell).lower().strip():
            return True
        return False
    
    def get_index(lst: list, search_list: list[str]):
        for index, element in enumerate(lst):
                # Compare the lowercase versions of the strings
                element = str(element).strip().casefold()
                for search in search_list:
                    if str(element).casefold() == search.casefold():
                        return index
        return None
    
    def get_column_ids(header: list):
        label_col_id = get_index(header, ["Label", "Class"])
        timestamp_col_id = get_index(header, ["Time", "Timestamp"])
        src_ip_col_id = get_index(header, ["Source", "Source-IP", "Source_IP", "Source IP", "Src", "Src_IP", "Src-IP", "Src_IP", "Src IP"])
        src_port_col_id = get_index(header, ["Source Port", "Source-Port", "Source_Port", "Src_Port", "Src-Port", "Src Port"])
        dst_ip_col_id = get_index(header, ["Destination", "Destination-IP", "Destination_IP", "Destination IP", "Dst", "Dst_IP", "Dst-IP", "Dst IP"])
        dst_port_col_id = get_index(header, ["Destination Port", "Destination-Port", "Destination_Port", "Dst_Port", "Dst-Port", "Dst Port"])
        return label_col_id,timestamp_col_id, src_ip_col_id, src_port_col_id, dst_ip_col_id, dst_port_col_id
    
    ######################################
    ### Beginning of the actual method ###
    ######################################
    TP = TN = FN = FP = 0

    # save in a dict for performance reasons 
    alerts_dict = {}
    for alert in alerts:
        timestamp, source_ip, source_port, destination_ip, destination_port = extract_ts_srcip_srcport_dstip_dstport_from_alert(alert)
        key = f"{timestamp}-{source_ip}-{source_port}-{destination_ip}-{destination_port}"
        # for each key, save all alerts from the ids that fall into that key (multiple possible, e.g. if ids says 1 request violates 2 rules)
        alerts_dict[key] = alerts_dict.get(key, []) + [alert]
            

    TOTAL_ALERTS = get_item_counts_of_dict(alerts_dict)
    # iterate over ground truth csv and compare each entry to the alerts
    with open(dataset.labels_file_path, 'r') as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)
        # Get column dynamically from header
        label_col_id, timestamp_col_id, src_ip_col_id, src_port_col_id, dst_ip_col_id, dst_port_col_id = get_column_ids(header)

        for row in reader:
            row_timestamp = normalize_and_parse_alert_timestamp(row[timestamp_col_id])
            row_source_ip = row[src_ip_col_id].strip()
            row_source_port = row[src_port_col_id].strip()
            row_destination_ip = row[dst_ip_col_id].strip()
            row_destination_port = row[dst_port_col_id].strip()
            key = f"{row_timestamp}-{row_source_ip}-{row_source_port}-{row_destination_ip}-{row_destination_port}"
            if key in alerts_dict:
                alert = alerts_dict[key].pop(0)
                # if the list is emptied, remove the key from the dict
                if alerts_dict[key] == []: 
                    del alerts_dict[key]
                if is_request_benign(row[label_col_id]):
                    FP += 1
                else:
                    TP += 1
            else:
                if is_request_benign(row[label_col_id]):
                    TN += 1
                else:
                    FN += 1
    # amount of alerts that could not be assigned to a label, for isntance if multiple alerts exist for 1 label
    UNASSIGNED_ALERTS = get_item_counts_of_dict(alerts_dict)
    LOGGER.debug(f"TP {TP}, FP {FP}, TN {TN}, FN {FN}, Unassigned: {UNASSIGNED_ALERTS} of {TOTAL_ALERTS}")

    return TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS

