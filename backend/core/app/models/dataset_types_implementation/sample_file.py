"""
The following methods are supposed to show how to add a new dataset type to the framework
    1. You should add the Dataset type in the DB by creating a new entry in the sql script before startup or using sql commands on a running instance
    2. Create a file in this directroy named like the "function_prefix" value you selected in the DB entry
    3. implement the following methods and be aware of the naming convetion!!
"""

from app.bicep_utils.models.ids_base import Alert

def your_prefix_get_benign_and_malicious_counts_of_labels_file(labels_file_text_stream):
    """
    Method to calculate how many entries of the dataset contain benign and malicious data

    Args:
        labels_file_text_stream: The text stream of the labels file containing the classes
    
    Returns:
        benign_count (int): Amount of benign data points
        malicious_count (int): Amount of malicious data points

    """
    # return benign_count, malicious_count
    pass

def your_prefix_get_positives_and_negatives_from_dataset(dataset, alerts: list[Alert]):
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
    # return TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS
    pass
