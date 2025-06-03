import csv
import ast
from datetime import datetime
from collections import defaultdict
from statistics import mean, stdev
from typing import List, Dict, Tuple


def parse_metrics(metrics_str: str) -> Dict[str, float]:
    """Safely parse the Metrics string into a dictionary."""
    return ast.literal_eval(metrics_str)


def compute_runtime(start: str, end: str) -> float:
    """Compute runtime in seconds from ISO timestamp strings."""
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    return (end_dt - start_dt).total_seconds()


def read_data(file_path: str, extra_metric: str = 'RUNTIME_SECONDS') -> Dict[str, Dict[str, List[float]]]:
    """Read CSV and aggregate metrics per IDS configuration."""
    aggregated: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            ids = row['IDS'].strip()
            metrics = parse_metrics(row['Metrics'])
            runtime = float(row['Runtime']) # compute_runtime(row['Start'], row['End'])
            metrics[extra_metric] = runtime

            for key, value in metrics.items():
                aggregated[ids][key].append(value)

    return aggregated


def format_mean_std(values: List[float]) -> str:
    """Format mean ± stddev or single value."""
    if not values:
        return "N/A"
    if len(values) == 1:
        return f"{values[0]:.2f}"
    return f"{mean(values):.2f} $\\pm$ {stdev(values):.2f}"


def write_latex_table(data: Dict[str, Dict[str, List[float]]], metric_keys: List[str], output_file: str):
    """Write LaTeX table summarizing metric averages and standard deviations."""
    with open(output_file, "w") as texfile:
        texfile.write("\\begin{table*}[t]\n")
        texfile.write("    \\centering\n")
        texfile.write("    \\caption{Aggregated performance over CTU-13, CICIDS2017, and UNSW-NB15 datasets}\n")
        texfile.write("    \\label{tab:ids_performance_aggregated}\n")
        texfile.write("    \\renewcommand{\\arraystretch}{1.5}\n")
        texfile.write("    \\begin{tabular}{l" + "c" * len(metric_keys) + "}\n")
        texfile.write("        \\toprule\n")
        texfile.write("        \\textbf{IDS} & " + " & ".join(f"\\textbf{{{k.replace('_', ' ').title()}}}" for k in metric_keys) + " \\\\\n")
        texfile.write("        \\midrule\n")

        for ids, metrics in data.items():
            row = [ids] + [format_mean_std(metrics.get(key, [])) for key in metric_keys]
            texfile.write("        " + " & ".join(row) + " \\\\\n")

        texfile.write("        \\bottomrule\n")
        texfile.write("    \\end{tabular}\n")
        texfile.write("\\end{table*}\n")


def main():
    input_csv = "./benchmarking_results/ids_results_full_datasets.csv"
    output_tex = "./benchmarking_results/aggregated_ids_results.tex"
    metric_keys = [
        'FPR', 'FNR', 'DR', 'FDR', 'ACCURACY', 'PRECISION',
        'F_SCORE', 'UNASSIGNED_ALERTS_RATIO', 'RUNTIME_SECONDS'
    ]

    data = read_data(input_csv)
    write_latex_table(data, metric_keys, output_tex)


if __name__ == "__main__":
    main()
