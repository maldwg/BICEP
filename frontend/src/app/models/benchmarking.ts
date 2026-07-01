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
  repeat_count: number,
  mode: 'static_dataset' | 'throughput',
  traffic_mode?: 'packet_generator' | 'iperf',
  packet_count?: number,
  rate_pps?: number,
  payload_size?: number,
  protocol?: 'tcp' | 'udp' | 'icmp',
  source_ip?: string | null,
  destination_ip?: string | null,
  source_port?: number,
  destination_port?: number,
  payload?: string | null,
  iperf_duration?: number,
  iperf_parallel?: number,
  iperf_protocol?: 'tcp' | 'udp',
  iperf_bandwidth?: string | null,
  analysis_wait_seconds?: number
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
  traffic_mode?: 'packet_generator' | 'iperf',
  packet_count?: number,
  bytes_sent?: number,
  traffic_runtime?: number,
  throughput_pps?: number,
  throughput_mbps?: number,
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
  mode: 'static_dataset' | 'throughput',
  traffic_mode?: 'packet_generator' | 'iperf',
  packet_count?: number,
  rate_pps?: number,
  payload_size?: number,
  protocol?: 'tcp' | 'udp' | 'icmp',
  source_ip?: string,
  destination_ip?: string,
  source_port?: number,
  destination_port?: number,
  iperf_duration?: number,
  iperf_parallel?: number,
  iperf_protocol?: 'tcp' | 'udp',
  iperf_bandwidth?: string,
  analysis_wait_seconds?: number,
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

export interface ThroughputResultItem {
  job_id: number,
  item_id: number,
  target_name: string,
  target_type: 'container' | 'ensemble',
  traffic_mode: 'packet_generator' | 'iperf',
  status: string,
  configuration_name?: string,
  ruleset_name?: string,
  repeat_index: number,
  repeat_total: number,
  packet_count?: number,
  bytes_sent?: number,
  traffic_runtime?: number,
  throughput_pps?: number,
  throughput_mbps?: number,
  started_at?: string,
  completed_at?: string
}
