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

export interface BenchmarkTargetSelection {
  target_type: 'container' | 'ensemble',
  target_id: number,
  configuration_ids: number[],
  ruleset_ids: number[]
}

export interface BenchmarkJobCreate {
  targets: BenchmarkTargetSelection[],
  dataset_ids: number[],
  settle_seconds: number,
  repeat_count: number
}

export interface BenchmarkingJobItem {
  id: number,
  job_id: number,
  position: number,
  status: string,
  target_type: 'container' | 'ensemble',
  target_id: number,
  target_name: string,
  dataset_id: number,
  dataset_name: string,
  configuration_id?: number,
  configuration_name?: string,
  ruleset_id?: number,
  ruleset_name?: string,
  repeat_index: number,
  repeat_total: number,
  started_at?: string,
  completed_at?: string,
  error?: string
}

export interface BenchmarkingJob {
  id: number,
  status: string,
  total_runs: number,
  completed_runs: number,
  settle_seconds: number,
  repeat_count: number,
  stop_requested: boolean,
  created_at: string,
  started_at?: string,
  completed_at?: string,
  error?: string,
  items: BenchmarkingJobItem[]
}

export interface BenchmarkingJobResponse {
  content: BenchmarkingJob
}

export interface BenchmarkingJobsResponse {
  content: BenchmarkingJob[]
}
