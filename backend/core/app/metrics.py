from .logger import LOGGER
from .database import get_db_session_context
from .models.dataset_types import get_all_dataset_types
from .models.dataset import get_dataset_by_id

async def calculate_evaluation_metrics(dataset_id, alerts):
    LOGGER.debug("start calculation of evaluation metrics")
    with get_db_session_context() as db: 
        dataset = get_dataset_by_id(dataset_id=dataset_id, db=db)
        true_benign = dataset.ammount_benign
        true_malicious = dataset.ammount_malicious
        total = true_benign + true_malicious
        TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS = await dataset.dataset_type.get_positives_and_negatives_from_dataset( dataset, alerts)

    def calculate_fpr():
        fpr = round(FP / (FP + TN), 2) if FP + TN > 0 else 0
        return fpr

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
        fdr = round(FP / (FP + TP), 2) if FP + TP > 0 else 0
        return fdr
    
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

    def calculate_unassigned_requests_ratio():
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
        "UNASSIGNED_ALERTS_RATIO": calculate_unassigned_requests_ratio()
    }
    LOGGER.debug(f"metrics: {metrics}")
    return metrics
