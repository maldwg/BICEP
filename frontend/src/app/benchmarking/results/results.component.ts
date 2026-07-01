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
import { ComparisonComponent } from './comparison/comparison.component';

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


  /** Columns displayed in the table. Columns IDs can be added, removed, or reordered. */
  displayedColumns = [
    'select', 'id', 'ids_name', 'dataset_name', 'ensembling_method', 'configuration_name', 'ruleset_name', 'start_time', 'stop_time', 'runtime',
    'detection_rate', 'fpr', 'fnr', 'fdr', 'acc', 'prec', 'f1_score', 'avg_cpu_usage', 'avg_memory_usage'];
  throughputDisplayedColumns = [
    'job_id', 'target_name', 'traffic_mode', 'configuration_name', 'ruleset_name', 'repeat', 'packet_count',
    'bytes_sent', 'traffic_runtime', 'throughput_pps', 'throughput_mbps', 'started_at', 'completed_at', 'status'
  ];

  selection = new SelectionModel<BenchmarkingResultsItem>(true, []);
  showComparison = false;

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

  toggleComparisonView() {
    const selectedItems = this.selection.selected;
    if (selectedItems.length < 2) {
      return;
    }
    this.showComparison = !this.showComparison;
  }


  chartOption = {
    radar: {
      indicator: [
        { name: 'A', max: 100 },
        { name: 'B', max: 100 },
        { name: 'C', max: 100 }
      ]
    },
    series: [{
      type: 'radar',
      data: [{ value: [80, 60, 70] }]
    }]
  };

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
    });
    this.loadThroughputResults();
    document.body.classList.add('no-body-background');
  }

  ngOnDestroy() {
    document.body.classList.remove('no-body-background');
  }

  applyFilter(value: string) {
    this.dataSource.setFilter(value);
    this.applyThroughputFilter(value);
  }
  applyFilters(value: string) {
    this.dataSource.setFilter(value);
    this.applyThroughputFilter(value);
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
        'Avg CPU (cores)', 'Avg RAM (MB)'
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
          row.avg_memory_usage ?? ''
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
      'Started', 'Completed', 'Status'
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

}
