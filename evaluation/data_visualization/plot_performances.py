import matplotlib.pyplot as plt
import matplotlib.pyplot as plt

def plot_chart(output_file, metrics, title):
    fig, ax = plt.subplots()
    metric_names = list(metrics.keys())
    metric_values = [metric * 100 for metric in metrics.values()]
    
    colors = {
        "FPR": 'red',            
        "FNR": 'orange',         
        "DR": 'green',
        "FDR": "#D65F3E",   # terracotta
        "ACCURACY": 'blue',      
        "PRECISION": 'purple',   
        "F_SCORE": 'teal',       
        "UNASSIGNED": 'gray' 
    }
    
    bar_colors = [colors[metric] for metric in metric_names]
    ax.bar(metric_names, metric_values, color=bar_colors)
    
    ax.set_ylabel('Values in %')
    ax.set_title(title)
    
    # Set the y-axis to always have the same scale from 0 to 100
    ax.set_ylim(0, 100)
    ax.set_yticks([i for i in range(0, 101, 10)])
    
    plt.xticks(rotation=90, ha='right')
    plt.tight_layout()
    plt.savefig(output_file, format='svg')



def calculate_metrics(TP, FP, FN, TN, TOTAL_ALERTS, UNASSIGNED_ALERTS):
    true_benign = FP + TN
    true_malicious = TP + FN
    total = true_benign + true_malicious
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

    def calculate_fdr():
        fdr = round(FP / (FP +TP), 2) if FP + TP > 0 else 0
        return fdr


    metrics = {
        "FPR": calculate_fpr(),
        "FNR": calculate_fnr(),
        "DR": calculate_dr(),
        "FDR": calculate_fdr(),
        "ACCURACY": calculate_accuracy(),
        "PRECISION": calculate_precision(),
        "F_SCORE": calculate_f_score(),
        "UNASSIGNED": calculate_unassigned_requests_ration()
    }

    return metrics
if __name__ == "__main__":
    metrics = calculate_metrics(TP=0, FP=0, TN=8526, FN=2093, TOTAL_ALERTS=0, UNASSIGNED_ALERTS=0)
    file_name = "/mnt/c/Users/Max/Desktop/suricata-slips-ensemble.svg"
    title = "Suricata and Slips ensemble"
    plot_chart(output_file=file_name, metrics=metrics, title=title)
    print(metrics)
# Suricata Alerts only
#metrics = calculate_metrics(TP=206896, FP=175432, TN=2097665, FN=350750, TOTAL_ALERTS=1011129, UNASSIGNED_ALERTS=628801)
#{'FPR': 0.08, 'FNR': 0.63, 'DR': 0.37, 'FDR': 0.46, 'ACCURACY': 0.81, 'PRECISION': 0.54, 'F_SCORE': 0.44, 'UNASSIGNED': 0.62}

# Suricata anomaly only
# #metrics = calculate_metrics(TP=261543, FP=487885, TN=1785212, FN=296103, TOTAL_ALERTS=2136694, UNASSIGNED_ALERTS=1387266)
# #{'FPR': 0.21, 'FNR': 0.53, 'DR': 0.47, 'FDR': 0.65, 'ACCURACY': 0.72, 'PRECISION': 0.35, 'F_SCORE': 0.4, 'UNASSIGNED': 0.65}

# # Suricata alerts and anomalies
# metrics = calculate_metrics(TP=261725, FP=578095, TN=1695002, FN=295921, TOTAL_ALERTS=3147890, UNASSIGNED_ALERTS=2308070)
# {'FPR': 0.25, 'FNR': 0.53, 'DR': 0.47, 'FDR': 0.69, 'ACCURACY': 0.69, 'PRECISION': 0.31, 'F_SCORE': 0.37, 'UNASSIGNED': 0.73}

# Suricata Ensemble
#    metrics = calculate_metrics(TP=206844, FP=88209, TN=2184888, FN=350802, TOTAL_ALERTS=637326, UNASSIGNED_ALERTS=342273)
# {'FPR': 0.04, 'FNR': 0.63, 'DR': 0.37, 'FDR': 0.3, 'ACCURACY': 0.84, 'PRECISION': 0.7, 'F_SCORE': 0.48, 'UNASSIGNED': 0.54}

#Suricata small ds
#    metrics = calculate_metrics(TP=43, FP=1017, TN=7509, FN=2050, TOTAL_ALERTS=3195, UNASSIGNED_ALERTS=2135)
#    {'FPR': 0.12, 'FNR': 0.98, 'DR': 0.02, 'FDR': 0.96, 'ACCURACY': 0.71, 'PRECISION': 0.04, 'F_SCORE': 0.03, 'UNASSIGNED': 0.67}


# Slips all
# metrics = calculate_metrics(TP=1365, FP=4959, TN=3567, FN=728, TOTAL_ALERTS=12862, UNASSIGNED_ALERTS=6538)
# {'FPR': 0.58, 'FNR': 0.35, 'DR': 0.65, 'FDR': 0.78, 'ACCURACY': 0.46, 'PRECISION': 0.22, 'F_SCORE': 0.33, 'UNASSIGNED': 0.51}

# Slips AI-only
# metrics = calculate_metrics(TP=0, FP=2, TN=8524, FN=2093, TOTAL_ALERTS=2, UNASSIGNED_ALERTS=0)
# {'FPR': 0.0, 'FNR': 1.0, 'DR': 0.0, 'FDR': 1.0, 'ACCURACY': 0.8, 'PRECISION': 0.0, 'F_SCORE': 0, 'UNASSIGNED': 0.0}


# Slips NO- AI-only
# metrics = calculate_metrics(TP=1365, FP=4946, TN=3580, FN=728, TOTAL_ALERTS=12711, UNASSIGNED_ALERTS=6400)
# {'FPR': 0.58, 'FNR': 0.35, 'DR': 0.65, 'FDR': 0.78, 'ACCURACY': 0.47, 'PRECISION': 0.22, 'F_SCORE': 0.33, 'UNASSIGNED': 0.5}

# Slips and Suricata Ensemble, reduced dataset
# metrics = calculate_metrics(TP=0, FP=0, TN=8526, FN=2093, TOTAL_ALERTS=0, UNASSIGNED_ALERTS=0)
# {'FPR': 0.0, 'FNR': 1.0, 'DR': 0.0, 'FDR': 0, 'ACCURACY': 0.8, 'PRECISION': 0, 'F_SCORE': 0, 'UNASSIGNED': 0}

# Slips ensemble 
# # metrics = calculate_metrics(TP=0, FP=0, TN=8526, FN=2093, TOTAL_ALERTS=0, UNASSIGNED_ALERTS=0)
# {'FPR': 0.0, 'FNR': 1.0, 'DR': 0.0, 'FDR': 0, 'ACCURACY': 0.8, 'PRECISION': 0, 'F_SCORE': 0, 'UNASSIGNED': 0}