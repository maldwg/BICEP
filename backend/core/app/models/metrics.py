
import csv

from ..bicep_utils.models.ids_base import Alert
from datetime import datetime, timezone

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
    return metrics

async def calculate_evaluation_metrics_for_ensemble():
    pass

async def get_positves_and_negatives_from_dataset(dataset, alerts: list[Alert]):
    TP = 0
    FP = 0
    TN = 0
    FN = 0
    timestamp_format = "%d/%m/%Y %H:%M:%S"

    async def get_index(lst: list, search_list: list[str]):
        for index, element in enumerate(lst):
                # Compare the lowercase versions of the strings
                for search in search_list:
                    if element.casefold() == search.casefold():
                        return index
        return None


    with dataset.labels_file as input_csv:
        reader = csv.reader(input_csv)
        header = next(reader)
        header_list = header.split(",")
        # Get column dynamically from header
        label_col_id =  await get_index(header_list, ["Label", "Class"])
        timestamp_col_id = await get_index(header_list, ["Time", "Timestamp"])
        src_ip_col_id = await get_index(header_list, ["Source", "Source-IP", "Source_IP", "Source IP", "Src", "Src_IP", "Src-IP", "Src_IP", "Src IP"])
        src_port_col_id = await get_index(header_list, ["Source Port", "Source-Port", "Source_Port", "Src_Port", "Src-Port", "Src Port"])
        dst_ip_col_id = await get_index(header_list, ["Destination", "Destination-IP", "Destination_IP", "Destination IP", "Dst", "Dst_IP", "Dst-IP", "Dst IP"])
        dst_port_col_id = await get_index(header_list, ["Destination Port", "Destination-Port", "Destination_Port", "Dst_Port", "Dst-Port", "Dst Port"])

        for row in reader:
            timestamp = datetime.fromisoformat(row[timestamp_col_id], format=timestamp_format, tz=timezone.utc)
            found_alert = False
            for alert in alerts:
                source_ip = alert.source.split(":")[0]
                source_port = alert.source.split(":")[-1]
                destination_ip = alert.destination.split(":")[0]
                destination_port = alert.destination.split(":")[-1]
                timestamp = datetime.fromisoformat(alert.time, format=timestamp_format, tz=timezone.utc)
                # check if match can be found in all alerts
                if (    
                    timestamp == row[timestamp_col_id] and
                    source_ip == row[src_ip_col_id] and
                    source_port == row[src_port_col_id] and
                    destination_ip == row[dst_ip_col_id] and
                    destination_port == row[dst_port_col_id]
                    ):
                    found_alert = True
                    if is_request_benign(row[label_col_id]):
                        FP += 1
                        break
                    else:
                        TP += 1
                        break

            if not found_alert:
                if is_request_benign(row[label_col_id]):
                    TN += 1
                else:
                    FN += 1


def is_request_benign(cell):
    if "benign" == str(cell).lower():
        return True
    return False