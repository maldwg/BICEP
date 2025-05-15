import csv
from collections import defaultdict
from statistics import mean, stdev
from pathlib import Path

# Define metric columns to be aggregated
METRIC_COLUMNS = [
    "FPR", "FNR", "DR", "FDR",
    "Accuracy", "Precision", "F1-score", "Unassigned Ratio", "Runtime (seconds)"
]

def read_csv_group_by_configuration(csv_path):
    grouped = defaultdict(lambda: defaultdict(list))
    with open(csv_path, newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            config = row["IDS"].strip()
            for metric in METRIC_COLUMNS:
                value = float(row[metric])
                grouped[config][metric].append(value)
    return grouped

def aggregate(grouped_data):
    aggregated = []
    for config, metrics in grouped_data.items():
        row = {"IDS": config}
        for metric, values in metrics.items():
            avg = mean(values)
            std = stdev(values) if len(values) > 1 else 0.0
            row[metric] = f"{avg:.2f} ± {std:.2f}"
        aggregated.append(row)
    return aggregated

# Generate LaTeX table
def write_latex_table(aggregated, output_path):
    with open(output_path, "w") as f:
        f.write("\\begin{table*}[t]\n")
        f.write("\\centering\n")
        f.write("\\caption{Performance of IDS configurations aggregated over multiple datasets}\n")
        f.write("\\label{tab:ids_performance_summary}\n")
        f.write("\\renewcommand{\\arraystretch}{1.5}\n")
        f.write("\\begin{tabular}{l" + "c" * len(METRIC_COLUMNS) + "}\n")
        f.write("\\toprule\n")
        f.write("\\textbf{IDS Configuration} & " + " & ".join(f"\\textbf{{{m}}}" for m in METRIC_COLUMNS) + " \\\\\n")
        f.write("\\midrule\n")
        for row in aggregated:
            line = f"{row['IDS']} & " + " & ".join(row[m] for m in METRIC_COLUMNS) + " \\\\\n"
            f.write(line)
        f.write("\\bottomrule\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table*}\n")
# Main
if __name__ == "__main__":
    input_csv = "./benchmarking_results/sample_ids_results.csv"  # Update if needed
    output_tex = "./benchmarking_results/aggregated_ids_results.tex"

    grouped = read_csv_group_by_configuration(input_csv)
    aggregated = aggregate(grouped)
    write_latex_table(aggregated, output_tex)

    print(f"LaTeX table written to: {output_tex}")
