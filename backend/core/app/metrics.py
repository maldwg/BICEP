import logging

from app.models.dataset import get_dataset_by_id

logger = logging.getLogger('bicep.metrics')

async def calculate_evaluation_metrics(db, dataset_id, alerts):
    logger.debug("start calculation of evaluation metrics")
    dataset = await get_dataset_by_id(db, dataset_id=dataset_id)
    true_benign = dataset.ammount_benign
    true_malicious = dataset.ammount_malicious
    total = true_benign + true_malicious
    TP, FP, TN, FN, UNASSIGNED_ALERTS, TOTAL_ALERTS = await dataset.dataset_type.get_positives_and_negatives_from_dataset( dataset, alerts)

    def ratio(numerator, denominator):
        return numerator / denominator if denominator > 0 else 0

    def calculate_fpr():
        return round(ratio(FP, FP + TN), 4)

    def calculate_fnr():
        return round(ratio(FN, FN + TP), 4)

    def calculate_dr():
        if true_malicious == 0:
            return 1
        return round(ratio(TP, TP + FN), 4)

    def calculate_fdr():
        return round(ratio(FP, FP + TP), 4)

    def calculate_accuracy():
        return round(ratio(TP + TN, total), 4)

    def calculate_precision():
        return round(ratio(TP, TP + FP), 4)

    def calculate_f_score():
        precision = ratio(TP, TP + FP)
        recall = ratio(TP, TP + FN)
        return round(
            2 * precision * recall / (precision + recall)
            if precision + recall > 0
            else 0,
            4,
        )

    def calculate_unassigned_requests_ratio():
        return round(ratio(UNASSIGNED_ALERTS, TOTAL_ALERTS), 4)

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
    if getattr(dataset, "evaluation_mode", "binary") == "multiclass":
        class_detection = await dataset.dataset_type.get_class_detection_statistics(
            dataset, alerts
        )
        metrics["PER_CLASS"] = class_detection["classes"]
        metrics["UNASSIGNED_ALERTS"] = class_detection["unassigned_alerts"]
    return metrics
