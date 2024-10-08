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
        return round(FP / (FP +TP), 2)

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
    metrics = calculate_metrics(TP=1756, FP=6681, TN=4686, FN=1035, TOTAL_ALERTS=16281, UNASSIGNED_ALERTS=7844)
    file_name = "/mnt/c/Users/Max/Desktop/slips-no-ai-only-static.svg"
    title = "Slips - No AI modules"
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
#    metrics = calculate_metrics(TP=58, FP=1217, TN=10150, FN=2733, TOTAL_ALERTS=4184, UNASSIGNED_ALERTS=2909)
#    {'FPR': 0.11, 'FNR': 0.98, 'DR': 0.02, 'FDR': 0.95, 'ACCURACY': 0.72, 'PRECISION': 0.05, 'F_SCORE': 0.03, 'UNASSIGNED': 0.7}


# Slips all
# metrics = calculate_metrics(TP=1668, FP=5045, TN=6322, FN=1123, TOTAL_ALERTS=13929, UNASSIGNED_ALERTS=7216)
# {'FPR': 0.44, 'FNR': 0.4, 'DR': 0.6, 'FDR': 0.75, 'ACCURACY': 0.56, 'PRECISION': 0.25, 'F_SCORE': 0.35, 'UNASSIGNED': 0.52}

# Slips AI-only
# metrics = calculate_metrics(TP=0, FP=3429, TN=7938, FN=2791, TOTAL_ALERTS=6156, UNASSIGNED_ALERTS=2727)
# {'FPR': 0.3, 'FNR': 1.0, 'DR': 0.0, 'FDR': 1.0, 'ACCURACY': 0.56, 'PRECISION': 0.0, 'F_SCORE': 0, 'UNASSIGNED': 0.44}


# Slips NO- AI-only
# metrics = calculate_metrics(TP=1756, FP=6681, TN=4686, FN=1035, TOTAL_ALERTS=16281, UNASSIGNED_ALERTS=7844)
# {'FPR': 0.59, 'FNR': 0.37, 'DR': 0.63, 'FDR': 0.79, 'ACCURACY': 0.46, 'PRECISION': 0.21, 'F_SCORE': 0.32, 'UNASSIGNED': 0.48}