export interface BenchmarkingResultsItem {
  id: number;
  dataset_name: string,
  ids_name: string,
  ensembling_method: string,
  configuration_name?: string,
  ruleset_name?: string,
  start_time: string,
  stop_time: string,
  runtime: number,
  prec: number,
  detection_rate: number,
  f1_score: number,
  acc: number,
  fpr: number,
  fnr: number,
  fdr: number,
  avg_cpu_usage?: number,
  avg_memory_usage?: number
}
