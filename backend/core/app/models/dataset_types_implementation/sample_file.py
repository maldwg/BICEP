"""
This file is supposed to show how to add a new dataset type to the framework
1. You should add the Dataset type in the DB by creating a new entry in the sql script before startup or using sql commands on a running instance
2. Create a file in this directroy named like the "function_prefix" value you selected in the DB entry
3. implement the following methods and be aware of the naming convetion!!
"""

from app.bicep_utils.models.ids_base import Alert

def your_prefix_get_benign_and_malicious_counts_of_labels_file(labels_file_text_stream):
    """
    Gets an input stream of the labels file directly
    Should return benign_count, malicious_count as integers
    """
    # return benign_count, malicious_count
    pass

def your_prefix_get_positives_and_negatives_from_dataset(dataset, alerts: list[Alert]):
    """
    gets the dataset object as input, as well as the complete list of alerts
    Should return the total ammounts of TP, FP, TN, FN, How many alerts in total were processed and how many could not be processed
    """
    # return TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS
    pass
