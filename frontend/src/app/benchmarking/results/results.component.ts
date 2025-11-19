import { AfterViewInit, Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { MatTableModule, MatTable } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { ResultsDataSource } from '../../services/benchmarking/results';
import { MatIconModule } from '@angular/material/icon';
import { BenchmarkingResultsItem } from '../../models/benchmarking';
import { FormControl, NgModel, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { BenchmarkingService } from '../../services/benchmarking/benchmarking.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { NgxEchartsModule } from 'ngx-echarts';

@Component({
  selector: 'app-results',
  templateUrl: './results.component.html',
  styleUrl: './results.component.scss',
  imports: [NgxEchartsModule, MatTableModule, MatPaginatorModule, MatSortModule, MatIconModule, CommonModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatButtonModule],
})
export class ResultsComponent implements AfterViewInit, OnInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<BenchmarkingResultsItem>;


  constructor(private benchmarkingService: BenchmarkingService) { }

  dataSource = new ResultsDataSource(this.benchmarkingService);
  searchControl = new FormControl('');


  /** Columns displayed in the table. Columns IDs can be added, removed, or reordered. */
  displayedColumns = [
    'id', 'ids_name', 'dataset_name', 'ensembling_method', 'start_time', 'stop_time', 'runtime',
    'detection_rate', 'fpr', 'fnr', 'fdr', 'acc', 'prec', 'f1_score'];


  chartOption = {
    radar: { indicator: [
      { name: 'A', max: 100 },
      { name: 'B', max: 100 },
      { name: 'C', max: 100 }
    ]},
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
    });
    document.body.classList.add('no-body-background');
  }

  ngOnDestroy() {
    document.body.classList.remove('no-body-background');
  }

  applyFilter(value: string) {
    this.dataSource.setFilter(value);
  }
  applyFilters(value: string) {
    this.dataSource.setFilter(value);
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
        'ID', 'IDS Name', 'Dataset', 'Ensemble Method', 'Start Time', 'Stop Time',
        'Runtime', 'Detection Rate', 'FPR', 'FNR', 'FDR', 'Accuracy', 'Precision', 'F1 Score'
      ];

      // Convert data to CSV rows
      const csvRows = [
        headers.join(','), // Header row
        ...data.map(row => [
          row.id,
          this.escapeCsvValue(row.ids_name),
          this.escapeCsvValue(row.dataset_name),
          this.escapeCsvValue(row.ensembling_method),
          this.escapeCsvValue(row.start_time),
          this.escapeCsvValue(row.stop_time),
          row.runtime,
          row.detection_rate,
          row.fpr,
          row.fnr,
          row.fdr,
          row.acc,
          row.prec,
          row.f1_score
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

  // Helper method to escape CSV values that contain commas, quotes, or newlines
  private escapeCsvValue(value: any): string {
    if (value == null) return '';
    const stringValue = String(value);
    if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
      return `"${stringValue.replace(/"/g, '""')}"`;
    }
    return stringValue;
  }

}
