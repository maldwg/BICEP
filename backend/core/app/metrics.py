
import csv
import io
import aiofiles
from .bicep_utils.models.ids_base import Alert
from datetime import datetime, timezone
from .utils import extract_ts_srcip_srcport_dstip_dstport_from_alert, normalize_and_parse_alert_timestamp
async def calculate_evaluation_metrics(dataset, alerts):
    true_benign = dataset.ammount_benign
    true_malicious = dataset.ammount_malicious
    total = true_benign + true_malicious
    TP, FP, TN, FN, UNASSIGNED_REQUESTS, TOTAL_REQUESTS = await get_positves_and_negatives_from_dataset(dataset, alerts)
    # FPR: False Positive Rate
    def calculate_fpr():
        return FP / (FP + TN) if (FP + TN) > 0 else 0

    # FNR: False Negative Rate
    def calculate_fnr():
        return FN / (FN + TP) if (FN + TP) > 0 else 0

    # DR: Detection Rate (Sensitivity/Recall)
    def calculate_dr():
        return TP / (TP + FN) if (TP + FN) > 0 else 0

    # Accuracy
    def calculate_accuracy():
        return (TP + TN) / total if total > 0 else 0

    # Precision
    def calculate_precision():
        return TP / (TP + FP) if (TP + FP) > 0 else 0

    # F-Score (F1-Score)
    def calculate_f_score():
        precision = calculate_precision()
        recall = calculate_dr()
        return 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    def calculate_unassigned_requests_ration():
        if TOTAL_REQUESTS != 0:
            return UNASSIGNED_REQUESTS / TOTAL_REQUESTS
        else:
            return 0

    metrics = {
        "FPR": calculate_fpr(),
        "FNR": calculate_fnr(),
        "DR": calculate_dr(),
        "ACCURACY": calculate_accuracy(),
        "PRECISION": calculate_precision(),
        "F_SCORE": calculate_f_score(),
        "UNASSIGNED_REQUEST_RATIO": calculate_unassigned_requests_ration()
    }
    print(metrics)

    return metrics

async def calculate_evaluation_metrics_for_ensemble():
    pass

async def get_positves_and_negatives_from_dataset(dataset, alerts: list[Alert]):
    TP = 0
    FP = 0
    TN = 0
    FN = 0

    async def get_index(lst: list, search_list: list[str]):
        for index, element in enumerate(lst):
                # Compare the lowercase versions of the strings
                element = str(element).strip().casefold()
                for search in search_list:
                    if str(element).casefold() == search.casefold():
                        return index
        return None


    # save in a dict for performance reasons 
    alerts_dict = {}
    for alert in alerts:
        timestamp, source_ip, source_port, destination_ip, destination_port = await extract_ts_srcip_srcport_dstip_dstport_from_alert(alert)

        key = f"{timestamp}-{source_ip}-{source_port}-{destination_ip}-{destination_port}"
        # for each key, save all alerts from the ids that fall into that key (multiple possible, e.g. if ids says 1 request violates 2 rules)
        alerts_dict[key] = alerts_dict.get(key, []) + [alert]

    # print(50*"###")
    # try:
    #     print(alerts_dict)
    # except Exception as e:
    #     print(e)
    original_alert_size = 0
    for _,v in alerts_dict.items():
        original_alert_size += len(v)
    with open(dataset.labels_file_path, 'r') as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)
        # Get column dynamically from header
        label_col_id = await get_index(header, ["Label", "Class"])
        timestamp_col_id = await get_index(header, ["Time", "Timestamp"])
        src_ip_col_id = await get_index(header, ["Source", "Source-IP", "Source_IP", "Source IP", "Src", "Src_IP", "Src-IP", "Src_IP", "Src IP"])
        src_port_col_id = await get_index(header, ["Source Port", "Source-Port", "Source_Port", "Src_Port", "Src-Port", "Src Port"])
        dst_ip_col_id = await get_index(header, ["Destination", "Destination-IP", "Destination_IP", "Destination IP", "Dst", "Dst_IP", "Dst-IP", "Dst IP"])
        dst_port_col_id = await get_index(header, ["Destination Port", "Destination-Port", "Destination_Port", "Dst_Port", "Dst-Port", "Dst Port"])
        # print(50*"+++")

        for row in reader:
            row_timestamp = await normalize_and_parse_alert_timestamp(row[timestamp_col_id])
            row_source_ip = row[src_ip_col_id].strip()
            row_source_port = row[src_port_col_id].strip()
            row_destination_ip = row[dst_ip_col_id].strip()
            row_destination_port = row[dst_port_col_id].strip()

            key = f"{row_timestamp}-{row_source_ip}-{row_source_port}-{row_destination_ip}-{row_destination_port}"
            # try:
            #     print(key)
            # except Exception as e:
            #     print(e)
            if key in alerts_dict:
                alert = alerts_dict[key].pop(0)
                # if the list is emptied, remove the key from the dict
                if alerts_dict[key] == []: 
                    del alerts_dict[key]
                if await is_request_benign(row[label_col_id]):
                    FP += 1
                else:
                    TP += 1
            else:

                if await is_request_benign(row[label_col_id]):
                    TN += 1
                else:
                    FN += 1
    # ammount of alerts that could not be assigned to a label, for isntance if multiple alerts exist for 1 label
    remaining_unassigned_alerts = 0
    for _,v in alerts_dict.items():
        remaining_unassigned_alerts += len(v)

    # try:        
    #     print(50*"---")
    #     print(alerts_dict)
    # except Exception as e:
    #     print(e)
    print(f"TP {TP}, FP {FP}, TN {TN}, FN {FN}, Unassigned: {remaining_unassigned_alerts} of {original_alert_size}")
    UNASSIGNED_REQUESTS = remaining_unassigned_alerts
    TOTAL_REQUESTS = original_alert_size

    return TP, FP, TN, FN, UNASSIGNED_REQUESTS, TOTAL_REQUESTS

async def is_request_benign(cell):
    if "benign" == str(cell).lower():
        return True
    return False


