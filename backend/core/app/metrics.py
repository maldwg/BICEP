
import csv
import io
from .bicep_utils.models.ids_base import Alert
from datetime import datetime, timezone
from dateutil import parser

async def calculate_evaluation_metrics(dataset, alerts):
    true_benign = dataset.ammount_benign
    true_malicious = dataset.ammount_malicious
    total = true_benign + true_malicious
    TP, FP, TN, FN = await get_positves_and_negatives_from_dataset(dataset, alerts)
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


    metrics = {
        "FPR": calculate_fpr(),
        "FNR": calculate_fnr(),
        "DR": calculate_dr(),
        "ACCURACY": calculate_accuracy(),
        "PRECISION": calculate_precision(),
        "F_SCORE": calculate_f_score()
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
        source_ip = alert.source.rsplit(":", maxsplit=1)[0].strip()
        source_port = alert.source.rsplit(":", maxsplit=1)[-1].strip()
        destination_ip = alert.destination.rsplit(":", maxsplit=1)[0].strip()
        destination_port = alert.destination.rsplit(":", maxsplit=1)[-1].strip()
        timestamp = await normalize_and_parse_timestamp(alert.time)

        key = (timestamp, source_ip, source_port, destination_ip, destination_port)
        alerts_dict[key] = alerts_dict.get(key, []) + [alert]

    original_alert_size = 0
    for _,v in alerts_dict.items():
        original_alert_size += len(v)
    csv_data = dataset.labels_file.decode("utf-8")
    with io.StringIO(csv_data) as input_csv:
        reader = csv.reader(input_csv)
        header = next(reader)
        # Get column dynamically from header
        label_col_id = await get_index(header, ["Label", "Class"])
        timestamp_col_id = await get_index(header, ["Time", "Timestamp"])
        src_ip_col_id = await get_index(header, ["Source", "Source-IP", "Source_IP", "Source IP", "Src", "Src_IP", "Src-IP", "Src_IP", "Src IP"])
        src_port_col_id = await get_index(header, ["Source Port", "Source-Port", "Source_Port", "Src_Port", "Src-Port", "Src Port"])
        dst_ip_col_id = await get_index(header, ["Destination", "Destination-IP", "Destination_IP", "Destination IP", "Dst", "Dst_IP", "Dst-IP", "Dst IP"])
        dst_port_col_id = await get_index(header, ["Destination Port", "Destination-Port", "Destination_Port", "Dst_Port", "Dst-Port", "Dst Port"])

        for row in reader:
            row_timestamp = await normalize_and_parse_timestamp(row[timestamp_col_id])
            source_ip = row[src_ip_col_id].strip()
            source_port = row[src_port_col_id].strip()
            destination_ip = row[dst_ip_col_id].strip()
            destination_port = row[dst_port_col_id].strip()

            key = (row_timestamp, source_ip, source_port, destination_ip, destination_port)
            # TODO 8: save all keys that weere iterated over to another dict and at the end remove all keys in the alert dioct that are the same as in the helper dict
            # because one request can trigger multiple alerts. Do not directly delete key on match as another request might be in the dataset to check 
            if key in alerts_dict:
                alert = alerts_dict[key].pop(0)
                # if the list is emptied, remove the key from the dict
                if not alerts_dict[key]: 
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
    counter = 0
    for _,v in alerts_dict.items():
        counter += len(v)
    # TODO 8: add counter/original to metrics to calculate 
    print(f"TP {TP}, FP {FP}, TN {TN}, FN {FN}, not assignable alerts {counter} of {original_alert_size}")
    return TP, FP, TN, FN

async def is_request_benign(cell):
    if "benign" == str(cell).lower():
        return True
    return False


async def normalize_and_parse_timestamp(timestamp_str):
    """
    Method to normalize timestamp formats, as these can differ from dataset to dataset
    Returns a normalized timestamp in minutes format
    """
    timestamp_format = "%d/%m/%Y %H:%M"
    parsed_timestamp = parser.parse(timestamp_str).strftime(timestamp_format)
    return parsed_timestamp