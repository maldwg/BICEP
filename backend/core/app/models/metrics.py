# TODO 10: implement calculations

def calculate_fpr():
    return 0.8
    pass

def calculate_fnr():
    return 0.7
    pass

def calculate_dr():
    return 1
    pass

def calculate_accuracy():
    return 0.5
    pass

def calculate_precision():
    return 0.8567
    pass

def calculate_f_score():
    return 0.999
    pass

async def calculate_evaluation_metrics():
    metrics = {
        "FPR": calculate_fpr(),
        "FNR": calculate_fnr(),
        "DR": calculate_dr(),
        "ACCURACY": calculate_accuracy(),
        "PRECISION": calculate_precision(),
        "F_SCORE": calculate_f_score()
    }
    return metrics

