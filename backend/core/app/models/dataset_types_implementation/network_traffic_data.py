"""
This implementation enables a user to use the following structure as datasets for the IDS:
    1. A pcap file with all the requests. May include background traffic, noise, etc.
    2. A CSV file with:
        a) information on the Source and Destintation (IP and Port), 
        b) timestamp in human-readable or Unix epoch form
        c) a label which contains the keyword "benign" or "malicious"
"""
import csv
import ipaddress
import logging
import re

from app.utils import (
    HourPrecision,
    MinutePrecision,
    SecondPrecision,
    MilisecondPrecision,
    get_precision_by_name,
    normalize_and_parse_alert_timestamp,
    parse_datetime_timestamp,
    extract_ts_srcip_srcport_dstip_dstport_from_alert,
    get_item_counts_of_dict,
    Precision,
)
from app.bicep_utils.models.ids_base import Alert
import random
from collections import Counter

BENIGN_CLASS_LABELS = {
    "benign",
    "normal",
    "normal traffic",
    "background",
    "background traffic",
    "legitimate",
    "clean",
    "non malicious",
    "non-malicious",
}


def _is_benign_label(label: str) -> bool:
    normalized = " ".join(str(label).strip().casefold().replace("_", " ").split())
    return normalized in BENIGN_CLASS_LABELS

logger = logging.getLogger('bicep.network_traffic_data')

def network_traffic_data_calculate_precision(labels_file_path):

    def get_header_and_sample_rows_from_csv(labels_file_path):
        with open(labels_file_path, "r", encoding="utf-8") as input:
            reader = csv.reader(input)
            header = next(reader)
            all_rows = list(reader)
        if not all_rows:
            raise ValueError("The labels CSV does not contain any data rows.")
        return header, random.sample(all_rows, min(5, len(all_rows)))

    def parse_timestamp(timestamp):
        return parse_datetime_timestamp(timestamp)

    # TODO 1: maybe enough to look for 0 values ? unliekly that everywhere there will be the same sec, ms, min, etc. 
    header, random_rows = get_header_and_sample_rows_from_csv(labels_file_path)
    _, timestamp_col_id, _, _, _, _ = _get_column_ids(header, random_rows)
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
    column_ids = _get_column_ids_for_file(labels_file_path)
    benign_count = 0
    malicious_count = 0
    with open(labels_file_path, "r", encoding="utf-8", newline="") as input_csv:
        reader = csv.reader(input_csv)
        header = next(reader)
        label_col_id = column_ids[0]
        for row in reader:
            if _is_benign_label(row[label_col_id]):
                benign_count += 1
            else:
                malicious_count += 1
    return benign_count, malicious_count


def network_traffic_data_get_class_counts(labels_file_path) -> dict[str, int]:
    column_ids = _get_column_ids_for_file(labels_file_path)
    with open(labels_file_path, "r", encoding="utf-8", newline="") as input_csv:
        reader = csv.reader(input_csv)
        header = next(reader)
        label_col_id = column_ids[0]
        counts = Counter()
        for row in reader:
            label = str(row[label_col_id]).strip()
            if not label:
                raise ValueError("Dataset labels must not be empty.")
            if len(label) > 256:
                raise ValueError("Dataset labels must not exceed 256 characters.")
            counts[label] += 1
    if not counts:
        raise ValueError("The labels CSV does not contain any data rows.")
    return dict(sorted(counts.items(), key=lambda item: item[0].casefold()))


def network_traffic_data_get_class_detection_statistics(
    dataset, alerts: list[Alert]
) -> dict:
    """Return alert coverage for each ground-truth class in a static dataset."""
    precision = get_precision_by_name(dataset.timestamp_precision)
    column_ids = _get_column_ids_for_file(dataset.labels_file_path)
    alerts_dict = {}
    for alert in alerts:
        key = extract_ts_srcip_srcport_dstip_dstport_from_alert(alert, precision)
        alerts_dict[key] = False

    class_stats: dict[str, dict[str, int | float | str | bool]] = {}
    with open(dataset.labels_file_path, "r", encoding="utf-8", newline="") as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)
        (
            label_col_id,
            timestamp_col_id,
            src_ip_col_id,
            src_port_col_id,
            dst_ip_col_id,
            dst_port_col_id,
        ) = column_ids

        for row in reader:
            label = str(row[label_col_id]).strip()
            if not label:
                raise ValueError("Dataset labels must not be empty.")
            if len(label) > 256:
                raise ValueError("Dataset labels must not exceed 256 characters.")
            row_stats = class_stats.setdefault(
                label,
                {
                    "class_label": label,
                    "is_benign": _is_benign_label(label),
                    "support": 0,
                    "detected": 0,
                    "missed": 0,
                },
            )
            row_stats["support"] += 1

            base_key = (
                normalize_and_parse_alert_timestamp(row[timestamp_col_id], precision),
                row[src_ip_col_id].strip(),
                row[src_port_col_id].strip(),
                row[dst_ip_col_id].strip(),
                row[dst_port_col_id].strip(),
            )
            reverse_key = _get_reverse_key(base_key)
            candidate_keys = (
                [base_key]
                + _get_keys_with_tolerance(base_key, precision)
                + [reverse_key]
                + _get_keys_with_tolerance(reverse_key, precision)
            )
            matching_key = next(
                (candidate for candidate in candidate_keys if candidate in alerts_dict),
                None,
            )
            if matching_key is None:
                row_stats["missed"] += 1
            else:
                alerts_dict[matching_key] = True
                row_stats["detected"] += 1

    for row_stats in class_stats.values():
        support = int(row_stats["support"])
        row_stats["detection_rate"] = round(
            int(row_stats["detected"]) / support if support else 0, 4
        )

    return {
        "classes": sorted(
            class_stats.values(), key=lambda item: str(item["class_label"]).casefold()
        ),
        "unassigned_alerts": _count_value_occurences_in_dict(alerts_dict, False),
        "total_alerts": len(alerts_dict),
    }


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
    column_ids = _get_column_ids_for_file(dataset.labels_file_path)
    # save in a dict for performance reasons 
    alerts_dict = {}
    for alert in alerts:
        timestamp, source_ip, source_port, destination_ip, destination_port = extract_ts_srcip_srcport_dstip_dstport_from_alert(alert, precision)
        key = (timestamp,source_ip,source_port,destination_ip,destination_port)
        # for each key, save all alerts from the ids that fall into that key (multiple possible, e.g. if ids says 1 request violates 2 rules)
        alerts_dict[key] = False
    TOTAL_ALERTS = len(alerts_dict.keys())# get_item_counts_of_dict(alerts_dict)
    
    # iterate over ground truth csv and compare each entry to the alerts
    with open(dataset.labels_file_path, 'r') as csv_file:
        reader = csv.reader(csv_file)
        header = next(reader)
        # Get column dynamically from header
        label_col_id, timestamp_col_id, src_ip_col_id, src_port_col_id, dst_ip_col_id, dst_port_col_id = column_ids
        direct_counter = 0
        tolerance_counter = 0
        reverse_tolerance_counter = 0
        else_counter = 0
        reverse_direct_counter = 0
        fp = 0
        tp = 0
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
                if key_found:
                    continue    
            # find plain reverse key == 1st level match
            if reverse_key in alerts_dict:
                _remove_key_from_dict(reverse_key, alerts_dict)
                if _is_request_benign(row[label_col_id]):
                    FP += 1
                    fp += 1
                else:
                    TP += 1
                    tp += 1
                reverse_direct_counter += 1                 
                continue 

            else:
                key_found = False
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
                if key_found:
                    continue
                
            else_counter += 1
            if _is_request_benign(row[label_col_id]):
                TN += 1
            else:
                FN += 1            
               
            # else:
            #     key_found = False
            #     keys_with_tolerance = _get_keys_with_tolerance(key=base_key, precision = precision)
            #     # try to find key for csv row + time buffer in alerts == 2. level match
            #     for key in keys_with_tolerance:
            #         if key in alerts_dict:
            #             _remove_key_from_dict(key, alerts_dict)
            #             if _is_request_benign(row[label_col_id]):
            #                 FP += 1
            #             else:
            #                 TP += 1
            #             key_found = True
            #             tolerance_counter += 1
            #             break
                # if not key_found:
                #     # try to find csv row reverse key with tolerance == 3. level match
                #     reverse_keys_with_tolerance = _get_keys_with_tolerance(key=reverse_key, precision = precision)
                #     for r_key in reverse_keys_with_tolerance:
                #         if r_key in alerts_dict:
                #             _remove_key_from_dict(r_key, alerts_dict)
                #             if _is_request_benign(row[label_col_id]):
                #                 FP += 1
                #             else:
                #                 TP += 1
                #             key_found = True
                #             reverse_tolerance_counter += 1
                #             break    
                # if no reversekey and normal key even with tolerance found == 4th level match                        
                # if not key_found:
                #     else_counter += 1
                #     if _is_request_benign(row[label_col_id]):
                #         TN += 1
                #     else:
                #         FN += 1
    print(f"tp {tp}, fp {fp}")
    total_matches = direct_counter + tolerance_counter + reverse_tolerance_counter + else_counter
    print(f"Direct matches: {direct_counter}, reverse direct matches {reverse_direct_counter},tolerance matches: {tolerance_counter}, reverse_matches {reverse_tolerance_counter}, else matches: {else_counter}")
    # amount of alerts that could not be assigned to a label, for isntance if multiple alerts exist for 1 label
    UNASSIGNED_ALERTS = _count_value_occurences_in_dict(alerts_dict, False)# get_item_counts_of_dict(alerts_dict)
    logger.debug(f"TP {TP}, FP {FP}, TN {TN}, FN {FN}, Unassigned: {UNASSIGNED_ALERTS} of {TOTAL_ALERTS}")

    return TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS



## helper methods
def _count_value_occurences_in_dict(dictionary, value):
    return sum(v == value for v in dictionary.values())

def _remove_key_from_dict(key, dict):
    dict[key] = True
    # dict[key].pop(0)
    #if dict[key] == []: 
    #    del dict[key]    

def _get_reverse_key(key):
    ts, src_ip, src_port, dst_ip, dst_port = key
    return (ts, dst_ip, dst_port, src_ip, src_port)

def _is_request_benign(cell: str) -> bool:
    return _is_benign_label(cell)

_COLUMN_NAME_PATTERNS = {
    "label": re.compile(
        r"^(?:(?:traffic|event|attack|groundtruth)?labels?|"
        r"(?:traffic|event|attack|groundtruth)?class(?:ification)?|"
        r"category|target|attack(?:type|cat(?:egory)?)?)$"
    ),
    "timestamp": re.compile(
        r"^(?:time(?:stamp)?|datetime|dateandtime|stime|starttime|"
        r"flowstart(?:time)?|eventtime(?:stamp)?|epoch(?:time)?|"
        r"unix(?:epoch)?(?:time|timestamp)?|ts|"
        r"bidirectionalfirstseen(?:ms|us|ns|s)?)$"
    ),
    "source_ip": re.compile(
        r"^(?:(?:ipv[46])?(?:src|source|client|origin)"
        r"(?:ip(?:addr(?:ess)?)?|addr(?:ess)?)?|(?:id)?origh)$"
    ),
    "source_port": re.compile(
        r"^(?:(?:src|source|client|origin)(?:port|p)|sport|(?:id)?origp)$"
    ),
    "destination_ip": re.compile(
        r"^(?:(?:ipv[46])?(?:dst|dest|destination|server|responder)"
        r"(?:ip(?:addr(?:ess)?)?|addr(?:ess)?)?|(?:id)?resph)$"
    ),
    "destination_port": re.compile(
        r"^(?:(?:dst|dest|destination|server|responder)(?:port|p)|"
        r"dport|dsport|(?:id)?respp)$"
    ),
}

_COLUMN_DISPLAY_NAMES = {
    "label": "label",
    "timestamp": "timestamp",
    "source_ip": "source IP",
    "source_port": "source port",
    "destination_ip": "destination IP",
    "destination_port": "destination port",
}


def _normalize_column_name(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().casefold())


def _sample_column_values(sample_rows: list[list[str]], column_id: int) -> list[str]:
    return [
        str(row[column_id]).strip()
        for row in sample_rows
        if column_id < len(row) and str(row[column_id]).strip()
    ]


def _matching_ratio(values: list[str], predicate) -> float:
    if not values:
        return 0.0
    return sum(bool(predicate(value)) for value in values) / len(values)


def _is_ip_value(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _is_port_value(value: str) -> bool:
    try:
        numeric_value = float(value)
    except ValueError:
        return False
    return numeric_value.is_integer() and 0 <= numeric_value <= 65535


def _is_timestamp_value(value: str) -> bool:
    try:
        numeric_value = float(value)
        if abs(numeric_value) <= 65535:
            return False
    except ValueError:
        pass
    try:
        parsed = parse_datetime_timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return 1970 <= parsed.year <= 2200


def _assign_single_typed_column(
    role: str, resolved: dict[str, int], candidates: list[tuple[float, int]]
) -> None:
    if role in resolved or not candidates:
        return
    candidates.sort(reverse=True)
    best_score, best_index = candidates[0]
    tied = [index for score, index in candidates if score == best_score]
    if best_score >= 0.8 and len(tied) == 1:
        resolved[role] = best_index


def _assign_directional_pair(
    source_role: str,
    destination_role: str,
    resolved: dict[str, int],
    candidates: list[int],
) -> None:
    missing_roles = [
        role for role in (source_role, destination_role) if role not in resolved
    ]
    available = sorted(index for index in candidates if index not in resolved.values())
    if len(missing_roles) == 1 and len(available) == 1:
        resolved[missing_roles[0]] = available[0]
    elif len(missing_roles) == 2 and len(available) == 2:
        # When names contain no direction at all, conventional CSV order is src,dst.
        resolved[source_role], resolved[destination_role] = available


def _infer_label_column(
    header: list, sample_rows: list[list[str]], resolved: dict[str, int]
) -> None:
    if "label" in resolved:
        return
    scored_candidates = []
    for index in range(len(header)):
        if index in resolved.values():
            continue
        values = _sample_column_values(sample_rows, index)
        if not values:
            continue
        normalized_values = {value.casefold() for value in values}
        benign_values = sum(_is_benign_label(value) for value in values)
        name = _normalize_column_name(header[index])
        name_hint = bool(re.search(r"(?:label|class|attack|category|target)", name))
        score = benign_values * 10 + (5 if name_hint else 0)
        if len(normalized_values) <= max(20, len(values) // 2):
            score += 1
        if score > 0:
            scored_candidates.append((score, index))
    scored_candidates.sort(reverse=True)
    if scored_candidates:
        best_score, best_index = scored_candidates[0]
        if len(scored_candidates) == 1 or best_score > scored_candidates[1][0]:
            resolved["label"] = best_index


def _get_column_ids_for_file(labels_file_path) -> tuple[int, int, int, int, int, int]:
    with open(labels_file_path, "r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)
        try:
            header = next(reader)
        except StopIteration as error:
            raise ValueError("The labels CSV is empty.") from error
        sample_rows = []
        for row in reader:
            if any(str(value).strip() for value in row):
                sample_rows.append(row)
            if len(sample_rows) >= 50:
                break
    if not sample_rows:
        raise ValueError("The labels CSV does not contain any data rows.")
    return _get_column_ids(header, sample_rows)


def _get_column_ids(
    header: list, sample_rows: list[list[str]] | None = None
) -> tuple[int, int, int, int, int, int]:
    """Resolve required fields by normalized names and conservative value inference."""
    normalized_header = [_normalize_column_name(value) for value in header]
    resolved: dict[str, int] = {}

    for role, pattern in _COLUMN_NAME_PATTERNS.items():
        matches = [
            index
            for index, name in enumerate(normalized_header)
            if pattern.fullmatch(name)
        ]
        if len(matches) == 1:
            resolved[role] = matches[0]
        elif len(matches) > 1:
            names = [str(header[index]) for index in matches]
            raise ValueError(
                f"Ambiguous {_COLUMN_DISPLAY_NAMES[role]} columns: {names}."
            )

    if sample_rows:
        used_indexes = set(resolved.values())
        timestamp_candidates = []
        ip_candidates = []
        port_candidates = []
        for index in range(len(header)):
            if index in used_indexes:
                continue
            values = _sample_column_values(sample_rows, index)
            timestamp_candidates.append(
                (_matching_ratio(values, _is_timestamp_value), index)
            )
            if _matching_ratio(values, _is_ip_value) >= 0.8:
                ip_candidates.append(index)
            if _matching_ratio(values, _is_port_value) >= 0.8:
                port_candidates.append(index)

        _assign_single_typed_column(
            "timestamp", resolved, timestamp_candidates
        )
        _assign_directional_pair(
            "source_ip", "destination_ip", resolved, ip_candidates
        )
        _assign_directional_pair(
            "source_port", "destination_port", resolved, port_candidates
        )
        _infer_label_column(header, sample_rows, resolved)

    role_order = (
        "label",
        "timestamp",
        "source_ip",
        "source_port",
        "destination_ip",
        "destination_port",
    )
    missing_roles = [role for role in role_order if role not in resolved]
    if missing_roles:
        missing_names = ", ".join(_COLUMN_DISPLAY_NAMES[role] for role in missing_roles)
        raise ValueError(
            f"Could not uniquely infer CSV columns for: {missing_names}. "
            f"Available headers: {[str(value) for value in header]}. "
            "Use recognizable field names when value-based inference is ambiguous."
        )

    logger.debug(
        "Resolved dataset CSV columns: %s",
        {role: str(header[resolved[role]]) for role in role_order},
    )
    return tuple(resolved[role] for role in role_order)

def _get_keys_with_tolerance(key, precision: Precision):
    # if the precision is second or milisecond than discrepancies are likely between pcap and csv 
    # therefor adjust the tolerance depending on the precision type of the dataset
    tolerance_unit = 1 if type(precision) in [MinutePrecision, HourPrecision] else 10
    timestamp = parse_datetime_timestamp(key[0])
    timestamps_with_tolerance = precision.calculate_timestamps_with_tolerance(timestamp, tolerance_unit=tolerance_unit)
    keys = []
    for ts in timestamps_with_tolerance:
        new_key = list(key)  
        new_key[0] = ts.replace(tzinfo=None).strftime(precision.timestamp_format)
        keys.append(tuple(new_key))
    return keys

