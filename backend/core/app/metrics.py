
import csv
import io
import aiofiles
import json
from .bicep_utils.models.ids_base import Alert
from datetime import datetime, timezone
from .utils import extract_ts_srcip_srcport_dstip_dstport_from_alert, normalize_and_parse_alert_timestamp
async def calculate_evaluation_metrics(dataset, alerts):
    print("start calculation")
    true_benign = dataset.ammount_benign
    true_malicious = dataset.ammount_malicious
    total = true_benign + true_malicious
    print("got benign malicious etc.")
    TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS = await get_positves_and_negatives_from_dataset(dataset, alerts)

    # FPR: False Positive Rate
    def calculate_fpr():
        fpr = FP / (FP + TN) if (FP + TN) > 0 else 0
        return round(fpr, 2)

    # FNR: False Negative Rate
    def calculate_fnr():
        fnr = FN / (FN + TP) if (FN + TP) > 0 else 0
        return round(fnr, 2)
    # DR: Detection Rate (Sensitivity/Recall)
    def calculate_dr():
        dr = TP / (TP + FN) if (TP + FN) > 0 else 0
        # if there is no malicious return DR of 100 %
        dr = 1 if true_malicious == 0 and dr == 0 else dr
        return round(dr,2)
    def calculate_fdr():
        fdr = FP / (FP + TP)
        return round(fdr, 2)
    # Accuracy
    def calculate_accuracy():
        acc = (TP + TN) / total if total > 0 else 0
        return round(acc, 2)

    # Precision
    def calculate_precision():
        prec = TP / (TP + FP) if (TP + FP) > 0 else 0
        return round(prec, 2)

    # F-Score (F1-Score)
    def calculate_f_score():
        precision = calculate_precision()
        recall = calculate_dr()
        score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        return round(score,2)

    def calculate_unassigned_requests_ration():
        if TOTAL_ALERTS != 0:
            return round(UNASSIGNED_ALERTS / TOTAL_ALERTS, 2)
        else:
            return 0

    metrics = {
        "FPR": calculate_fpr(),
        "FNR": calculate_fnr(),
        "DR": calculate_dr(),
        "FDR": calculate_fdr(),
        "ACCURACY": calculate_accuracy(),
        "PRECISION": calculate_precision(),
        "F_SCORE": calculate_f_score(),
        "UNASSIGNED_ALERTS_RATIO": calculate_unassigned_requests_ration()
    }
    print(metrics)

    return metrics

async def calculate_evaluation_metrics_for_ensemble():
    pass

async def get_positves_and_negatives_from_dataset(dataset, alerts: list[Alert]):
    TP = TN = FN = FP = 0

    # save in a dict for performance reasons 
    alerts_dict = {}
    for alert in alerts:
        unsuccessful_counter = 0
        try:
            timestamp, source_ip, source_port, destination_ip, destination_port = await extract_ts_srcip_srcport_dstip_dstport_from_alert(alert)
            key = f"{timestamp}-{source_ip}-{source_port}-{destination_ip}-{destination_port}"
            # for each key, save all alerts from the ids that fall into that key (multiple possible, e.g. if ids says 1 request violates 2 rules)
            alerts_dict[key] = alerts_dict.get(key, []) + [alert]
        except:
            unsuccessful_counter +=1
    print(f"{unsuccessful_counter} log entries were parsed unsuccesfully")

    TOTAL_ALERTS = await get_item_counts_of_dict(alerts_dict)
    # iterate over ground truth csv and compare each entry to the alerts
    with open(dataset.labels_file_path, 'r') as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)
        # Get column dynamically from header
        label_col_id, timestamp_col_id, src_ip_col_id, src_port_col_id, dst_ip_col_id, dst_port_col_id = await get_column_ids(header)

        for row in reader:
            unsuccessful_csv_counter = 0
            try:
                row_timestamp = await normalize_and_parse_alert_timestamp(row[timestamp_col_id])
                row_source_ip = row[src_ip_col_id].strip()
                row_source_port = row[src_port_col_id].strip()
                row_destination_ip = row[dst_ip_col_id].strip()
                row_destination_port = row[dst_port_col_id].strip()
            except:
                unsuccessful_csv_counter += 1
                continue
            key = f"{row_timestamp}-{row_source_ip}-{row_source_port}-{row_destination_ip}-{row_destination_port}"
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
        print(f"{unsuccessful_csv_counter} lines of the csv were processed unsucesfully")
    # ammount of alerts that could not be assigned to a label, for isntance if multiple alerts exist for 1 label
    UNASSIGNED_ALERTS = await get_item_counts_of_dict(alerts_dict)
    print(f"TP {TP}, FP {FP}, TN {TN}, FN {FN}, Unassigned: {UNASSIGNED_ALERTS} of {TOTAL_ALERTS}")

    return TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS

async def is_request_benign(cell):
    if "benign" == str(cell).lower().strip():
        return True
    return False


async def get_index(lst: list, search_list: list[str]):
    for index, element in enumerate(lst):
            # Compare the lowercase versions of the strings
            element = str(element).strip().casefold()
            for search in search_list:
                if str(element).casefold() == search.casefold():
                    return index
    return None

async def get_column_ids(header: list):
    label_col_id = await get_index(header, ["Label", "Class"])
    timestamp_col_id = await get_index(header, ["Time", "Timestamp"])
    src_ip_col_id = await get_index(header, ["Source", "Source-IP", "Source_IP", "Source IP", "Src", "Src_IP", "Src-IP", "Src_IP", "Src IP"])
    src_port_col_id = await get_index(header, ["Source Port", "Source-Port", "Source_Port", "Src_Port", "Src-Port", "Src Port"])
    dst_ip_col_id = await get_index(header, ["Destination", "Destination-IP", "Destination_IP", "Destination IP", "Dst", "Dst_IP", "Dst-IP", "Dst IP"])
    dst_port_col_id = await get_index(header, ["Destination Port", "Destination-Port", "Destination_Port", "Dst_Port", "Dst-Port", "Dst Port"])
    return label_col_id,timestamp_col_id, src_ip_col_id, src_port_col_id, dst_ip_col_id, dst_port_col_id

async def get_item_counts_of_dict(d: dict):
    items = 0
    for _,v in d.items():
        items += len(v)
    return items