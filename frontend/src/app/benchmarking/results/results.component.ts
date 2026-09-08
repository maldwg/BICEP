import { AfterViewInit, Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { MatTableModule, MatTable } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { ResultsDataSource } from '../../services/benchmarking/results';
import { MatIconModule } from '@angular/material/icon';
import { SelectionModel } from '@angular/cdk/collections';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { BenchmarkingJob, BenchmarkingJobItem, BenchmarkingResultsItem, ThroughputResultItem } from '../../models/benchmarking';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { BenchmarkingService } from '../../services/benchmarking/benchmarking.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { NgxEchartsModule } from 'ngx-echarts';
import { ComparisonComponent, ComparisonItem, ComparisonMetric } from './comparison/comparison.component';

@Component({
  selector: 'app-results',
  templateUrl: './results.component.html',
  styleUrl: './results.component.scss',
  imports: [NgxEchartsModule, MatTableModule, MatPaginatorModule, MatSortModule, MatIconModule, CommonModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatButtonModule, MatCheckboxModule, ComparisonComponent],
})
export class ResultsComponent implements AfterViewInit, OnInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<BenchmarkingResultsItem>;



  constructor(private benchmarkingService: BenchmarkingService) { }

  dataSource = new ResultsDataSource(this.benchmarkingService);
  searchControl = new FormControl('');
  throughputResults: ThroughputResultItem[] = [];
  filteredThroughputResults: ThroughputResultItem[] = [];
  multiclassResults: BenchmarkingResultsItem[] = [];
  filteredMulticlassResults: BenchmarkingResultsItem[] = [];


  /** Columns displayed in the table. Columns IDs can be added, removed, or reordered. */
  displayedColumns = [
    'select', 'id', 'ids_name', 'dataset_name', 'ensembling_method', 'configuration_name', 'ruleset_name', 'start_time', 'stop_time', 'runtime',
    'detection_rate', 'fpr', 'fnr', 'fdr', 'acc', 'prec', 'f1_score', 'avg_cpu_usage', 'avg_memory_usage'];
  throughputDisplayedColumns = [
    'throughput_select', 'job_id', 'target_name', 'traffic_mode', 'configuration_name', 'ruleset_name', 'repeat', 'packet_count',
    'bytes_sent', 'traffic_runtime', 'throughput_pps', 'throughput_mbps', 'avg_cpu_usage', 'avg_memory_usage',
    'started_at', 'completed_at', 'status'
  ];

  selection = new SelectionModel<BenchmarkingResultsItem>(true, []);
  multiclassSelection = new SelectionModel<BenchmarkingResultsItem>(true, []);
  throughputSelection = new SelectionModel<ThroughputResultItem>(true, []);
  showComparison = false;
  comparisonTitle = '';
  comparisonSubtitle = '';
  comparisonItems: ComparisonItem[] = [];
  comparisonMetrics: ComparisonMetric[] = [];

  readonly binaryComparisonMetrics: ComparisonMetric[] = [
    { value: 'detection_rate', viewValue: 'Detection rate', max: 1 },
    { value: 'acc', viewValue: 'Accuracy', max: 1 },
    { value: 'f1_score', viewValue: 'F1 score', max: 1 },
    { value: 'prec', viewValue: 'Precision', max: 1 },
    { value: 'fpr', viewValue: 'False-positive rate', max: 1 },
    { value: 'fnr', viewValue: 'False-negative rate', max: 1 },
    { value: 'runtime', viewValue: 'Runtime (s)' },
    { value: 'avg_cpu_usage', viewValue: 'Average CPU (cores)' },
    { value: 'avg_memory_usage', viewValue: 'Average RAM (MB)' }
  ];

  readonly multiclassComparisonMetrics: ComparisonMetric[] = [
    { value: 'macro_detection_rate', viewValue: 'Macro malicious detection rate', max: 1 },
    { value: 'weighted_detection_rate', viewValue: 'Weighted malicious detection rate', max: 1 },
    { value: 'lowest_detection_rate', viewValue: 'Lowest malicious-class detection rate', max: 1 },
    { value: 'benign_false_detection_rate', viewValue: 'Benign false-detection rate', max: 1 },
    { value: 'class_count', viewValue: 'Class count' },
    { value: 'runtime', viewValue: 'Runtime (s)' },
    { value: 'avg_cpu_usage', viewValue: 'Average CPU (cores)' },
    { value: 'avg_memory_usage', viewValue: 'Average RAM (MB)' }
  ];

  readonly throughputComparisonMetrics: ComparisonMetric[] = [
    { value: 'throughput_pps', viewValue: 'Throughput (pps)' },
    { value: 'throughput_mbps', viewValue: 'Throughput (Mbps)' },
    { value: 'traffic_runtime', viewValue: 'Traffic runtime (s)' },
    { value: 'packet_count', viewValue: 'Packets' },
    { value: 'bytes_sent', viewValue: 'Bytes sent' },
    { value: 'avg_cpu_usage', viewValue: 'Average CPU (cores)' },
    { value: 'avg_memory_usage', viewValue: 'Average RAM (MB)' }
  ];

  /** Whether the number of selected elements matches the total number of rows. */
  isAllSelected() {
    const numSelected = this.selection.selected.length;
    const numRows = this.dataSource.data.length;
    return numSelected === numRows;
  }

  /** Selects all rows if they are not all selected; otherwise clear selection. */
  masterToggle() {
    this.isAllSelected() ?
      this.selection.clear() :
      this.dataSource.data.forEach((row: BenchmarkingResultsItem) => this.selection.select(row));
  }

  /** The label for the checkbox on the passed row */
  checkboxLabel(row?: BenchmarkingResultsItem): string {
    if (!row) {
      return `${this.isAllSelected() ? 'select' : 'deselect'} all`;
    }
    return `${this.selection.isSelected(row) ? 'deselect' : 'select'} row ${row.id}`;
  }

  openBinaryComparison() {
    this.openComparison(
      'Binary Benchmark Comparison',
      'Compare detection quality, runtime, and resource use across the selected binary benchmark results.',
      this.binaryComparisonMetrics,
      this.selection.selected.map(result => ({
        id: result.id,
        label: `${result.ids_name} · ${result.dataset_name} #${result.id}`,
        metrics: this.binaryMetrics(result)
      }))
    );
  }

  openMulticlassComparison() {
    this.openComparison(
      'Multiclass Benchmark Comparison',
      'Compare malicious-class coverage, benign false detections, runtime, and resource use across the selected multiclass results.',
      this.multiclassComparisonMetrics,
      this.multiclassSelection.selected.map(result => ({
        id: result.id,
        label: `${result.ids_name} · ${result.dataset_name} #${result.id}`,
        metrics: this.multiclassMetrics(result)
      }))
    );
  }

  openThroughputComparison() {
    this.openComparison(
      'Throughput Comparison',
      'Compare traffic capacity, runtime, and resource consumption across the selected throughput runs.',
      this.throughputComparisonMetrics,
      this.throughputSelection.selected.map(result => ({
        id: result.item_id,
        label: `${result.target_name} #${result.item_id}`,
        metrics: {
          throughput_pps: result.throughput_pps,
          throughput_mbps: result.throughput_mbps,
          traffic_runtime: result.traffic_runtime,
          packet_count: result.packet_count,
          bytes_sent: result.bytes_sent,
          avg_cpu_usage: result.avg_cpu_usage,
          avg_memory_usage: result.avg_memory_usage
        }
      }))
    );
  }

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }


  ngOnInit(): void {
    this.searchControl.valueChanges.subscribe(value => {
      console.log("Filtering with value:", value);
      this.dataSource.setFilter(value || '');
      this.applyThroughputFilter(value || '');
      this.applyMulticlassFilter(value || '');
    });
    this.loadThroughputResults();
    this.loadMulticlassResults();
    document.body.classList.add('no-body-background');
  }

  ngOnDestroy() {
    document.body.classList.remove('no-body-background');
  }

  applyFilter(value: string) {
    this.dataSource.setFilter(value);
    this.applyThroughputFilter(value);
    this.applyMulticlassFilter(value);
  }
  applyFilters(value: string) {
    this.dataSource.setFilter(value);
    this.applyThroughputFilter(value);
    this.applyMulticlassFilter(value);
  }

  loadThroughputResults() {
    this.benchmarkingService.getBenchmarkingJobs(100).subscribe({
      next: response => {
        this.throughputResults = response.content.flatMap(job => this.toThroughputRows(job));
        this.applyThroughputFilter(this.searchControl.value || '');
      },
      error: err => {
        console.error('Could not load throughput benchmark results.', err);
      }
    });
  }

  loadMulticlassResults() {
    this.benchmarkingService.getAllConfigurations().subscribe({
      next: results => {
        this.multiclassResults = results.filter(
          result => (result.evaluation_mode || 'binary') === 'multiclass'
        );
        this.applyMulticlassFilter(this.searchControl.value || '');
      },
      error: err => console.error('Could not load multiclass benchmark results.', err)
    });
  }

  downloadResultsAsCSV() {
    // Get all data from the service (not just the current page)
    this.benchmarkingService.getAllConfigurations().subscribe(data => {
      if (!data || data.length === 0) {
        console.warn('No data available to download');
        return;
      }

      // Define CSV headers based on displayed columns
      const headers = [
        'ID', 'IDS Name', 'Dataset', 'Ensemble Method', 'Configuration', 'Ruleset', 'Start Time', 'Stop Time',
        'Runtime', 'Detection Rate', 'FPR', 'FNR', 'FDR', 'Accuracy', 'Precision', 'F1 Score',
        'Avg CPU (cores)', 'Avg RAM (MB)', 'Evaluation Mode'
      ];

      // Convert data to CSV rows
      const csvRows = [
        headers.join(','), // Header row
        ...data.map(row => [
          row.id,
          this.escapeCsvValue(row.ids_name),
          this.escapeCsvValue(row.dataset_name),
          this.escapeCsvValue(row.ensembling_method),
          this.escapeCsvValue(row.configuration_name),
          this.escapeCsvValue(row.ruleset_name),
          this.escapeCsvValue(row.start_time),
          this.escapeCsvValue(row.stop_time),
          row.runtime,
          row.detection_rate,
          row.fpr,
          row.fnr,
          row.fdr,
          row.acc,
          row.prec,
          row.f1_score,
          row.avg_cpu_usage ?? '',
          row.avg_memory_usage ?? '',
          row.evaluation_mode || 'binary'
        ].join(','))
      ];

      // Create CSV content
      const csvContent = csvRows.join('\n');

      // Create blob and download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      link.setAttribute('href', url);
      link.setAttribute('download', `benchmarking_results_${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      URL.revokeObjectURL(url);
    });
  }

  downloadThroughputResultsAsCSV() {
    const hasFilter = Boolean(this.searchControl.value?.trim());
    const data = hasFilter ? this.filteredThroughputResults : this.throughputResults;
    if (!data || data.length === 0) {
      console.warn('No throughput data available to download');
      return;
    }

    const headers = [
      'Job ID', 'Item ID', 'Target', 'Target Type', 'Traffic Mode', 'Configuration', 'Ruleset', 'Repeat',
      'Packet Count', 'Bytes Sent', 'Runtime Seconds', 'Throughput pps', 'Throughput Mbps',
      'Avg CPU (cores)', 'Avg RAM (MB)', 'Started', 'Completed', 'Status'
    ];
    const csvRows = [
      headers.join(','),
      ...data.map(row => [
        row.job_id,
        row.item_id,
        this.escapeCsvValue(row.target_name),
        row.target_type,
        row.traffic_mode,
        this.escapeCsvValue(row.configuration_name),
        this.escapeCsvValue(row.ruleset_name),
        `${row.repeat_index}/${row.repeat_total}`,
        row.packet_count ?? '',
        row.bytes_sent ?? '',
        row.traffic_runtime ?? '',
        row.throughput_pps ?? '',
        row.throughput_mbps ?? '',
        row.avg_cpu_usage ?? '',
        row.avg_memory_usage ?? '',
        this.escapeCsvValue(row.started_at),
        this.escapeCsvValue(row.completed_at),
        row.status
      ].join(','))
    ];

    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `throughput_results_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  }

  downloadMulticlassResultsAsCSV() {
    const rows = this.filteredMulticlassResults.flatMap(result =>
      (result.class_results || []).map(classResult => ({ result, classResult }))
    );
    if (rows.length === 0) {
      return;
    }
    const csvRows = [
      'Result ID,IDS Name,Dataset,Class,Class Type,Support,Outcome,Missed,Rate Type,Rate',
      ...rows.map(({ result, classResult }) => [
        result.id,
        this.escapeCsvValue(result.ids_name),
        this.escapeCsvValue(result.dataset_name),
        this.escapeCsvValue(classResult.class_label),
        classResult.is_benign ? 'benign' : 'malicious',
        classResult.support,
        classResult.detected,
        classResult.missed,
        classResult.is_benign ? 'false detection rate' : 'detection rate',
        classResult.detection_rate,
      ].join(','))
    ];
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = `multiclass_results_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  isAllMulticlassSelected(): boolean {
    return this.multiclassSelection.selected.length === this.filteredMulticlassResults.length;
  }

  toggleAllMulticlass(): void {
    this.isAllMulticlassSelected()
      ? this.multiclassSelection.clear()
      : this.filteredMulticlassResults.forEach(result => this.multiclassSelection.select(result));
  }

  isAllThroughputSelected(): boolean {
    return this.throughputSelection.selected.length === this.filteredThroughputResults.length;
  }

  toggleAllThroughput(): void {
    this.isAllThroughputSelected()
      ? this.throughputSelection.clear()
      : this.filteredThroughputResults.forEach(result => this.throughputSelection.select(result));
  }

  multiclassMacroDetectionRate(result: BenchmarkingResultsItem): number {
    const classes = this.maliciousClasses(result);
    return classes.length
      ? classes.reduce((total, item) => total + item.detection_rate, 0) / classes.length
      : 0;
  }

  multiclassWeightedDetectionRate(result: BenchmarkingResultsItem): number {
    const classes = this.maliciousClasses(result);
    const support = classes.reduce((total, item) => total + item.support, 0);
    return support
      ? classes.reduce((total, item) => total + item.detected, 0) / support
      : 0;
  }

  multiclassLowestDetectionRate(result: BenchmarkingResultsItem): number {
    const classes = this.maliciousClasses(result);
    return classes.length ? Math.min(...classes.map(item => item.detection_rate)) : 0;
  }

  multiclassBenignFalseDetectionRate(result: BenchmarkingResultsItem): number {
    const classes = (result.class_results || []).filter(item => item.is_benign);
    const support = classes.reduce((total, item) => total + item.support, 0);
    return support
      ? classes.reduce((total, item) => total + item.detected, 0) / support
      : 0;
  }

  // Helper method to escape CSV values that contain commas, quotes, or newlines
  private escapeCsvValue(value: any): string {
    if (value == null) return '';
    const stringValue = String(value);
    if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
      return `"${stringValue.replace(/"/g, '""')}"`;
    }
    return stringValue;
  }

  formatCpuUsage(value: number | null | undefined): string {
    if (value == null) {
      return '-';
    }

    const formattedValue = value.toFixed(5);
    if (Number(formattedValue) === 0) {
      return `~${formattedValue}`;
    }

    return formattedValue;
  }

  private toThroughputRows(job: BenchmarkingJob): ThroughputResultItem[] {
    if (job.mode !== 'throughput') {
      return [];
    }

    return job.items
      .filter(item => item.traffic_mode || item.dataset_id === 0)
      .map(item => this.toThroughputRow(job, item));
  }

  private toThroughputRow(job: BenchmarkingJob, item: BenchmarkingJobItem): ThroughputResultItem {
    return {
      job_id: job.id,
      item_id: item.id,
      target_name: item.target_name,
      target_type: item.target_type,
      traffic_mode: item.traffic_mode || job.traffic_mode || 'packet_generator',
      status: item.status,
      configuration_name: item.configuration_name,
      ruleset_name: item.ruleset_name,
      repeat_index: item.repeat_index,
      repeat_total: item.repeat_total,
      packet_count: item.packet_count ?? job.packet_count,
      bytes_sent: item.bytes_sent,
      traffic_runtime: item.traffic_runtime,
      throughput_pps: item.throughput_pps,
      throughput_mbps: item.throughput_mbps,
      avg_cpu_usage: item.avg_cpu_usage,
      avg_memory_usage: item.avg_memory_usage,
      started_at: item.started_at,
      completed_at: item.completed_at,
    };
  }

  private applyThroughputFilter(value: string) {
    const filterValue = value.trim().toLowerCase();
    if (!filterValue) {
      this.filteredThroughputResults = [...this.throughputResults];
      return;
    }

    this.filteredThroughputResults = this.throughputResults.filter(item =>
      Object.values(item)
        .map(v => (v == null ? '' : String(v).toLowerCase()))
        .join(' ')
        .includes(filterValue)
    );
  }

  private applyMulticlassFilter(value: string) {
    const filterValue = value.trim().toLowerCase();
    if (!filterValue) {
      this.filteredMulticlassResults = [...this.multiclassResults];
      return;
    }
    this.filteredMulticlassResults = this.multiclassResults.filter(result =>
      [
        result.id,
        result.ids_name,
        result.dataset_name,
        result.configuration_name,
        result.ruleset_name,
        ...(result.class_results || []).map(classResult => classResult.class_label)
      ]
        .map(value => value == null ? '' : String(value).toLowerCase())
        .join(' ')
        .includes(filterValue)
    );
  }

  private openComparison(
    title: string,
    subtitle: string,
    metrics: ComparisonMetric[],
    items: ComparisonItem[]
  ) {
    if (items.length < 2) {
      return;
    }
    this.comparisonTitle = title;
    this.comparisonSubtitle = subtitle;
    this.comparisonMetrics = metrics;
    this.comparisonItems = items;
    this.showComparison = true;
  }

  private binaryMetrics(result: BenchmarkingResultsItem): Record<string, number | undefined> {
    return {
      detection_rate: result.detection_rate,
      acc: result.acc,
      f1_score: result.f1_score,
      prec: result.prec,
      fpr: result.fpr,
      fnr: result.fnr,
      runtime: result.runtime,
      avg_cpu_usage: result.avg_cpu_usage,
      avg_memory_usage: result.avg_memory_usage
    };
  }

  private multiclassMetrics(result: BenchmarkingResultsItem): Record<string, number | undefined> {
    return {
      macro_detection_rate: this.multiclassMacroDetectionRate(result),
      weighted_detection_rate: this.multiclassWeightedDetectionRate(result),
      lowest_detection_rate: this.multiclassLowestDetectionRate(result),
      benign_false_detection_rate: this.multiclassBenignFalseDetectionRate(result),
      class_count: result.class_results?.length || 0,
      runtime: result.runtime,
      avg_cpu_usage: result.avg_cpu_usage,
      avg_memory_usage: result.avg_memory_usage
    };
  }

  private maliciousClasses(result: BenchmarkingResultsItem) {
    return (result.class_results || []).filter(item => !item.is_benign);
  }

}
