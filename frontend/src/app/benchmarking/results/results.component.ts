import { AfterViewInit, Component, ViewChild } from '@angular/core';
import { MatTableModule, MatTable } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { ResultsDataSource } from '../../services/benchmarking/results';
import { MatIconModule } from '@angular/material/icon';
import {BenchmarkingResultsItem} from '../../models/benchmarking';
import { FormControl, NgModel, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { BenchmarkingService } from '../../services/benchmarking/benchmarking.service';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
@Component({
  selector: 'app-results',
  templateUrl: './results.component.html',
  styleUrl: './results.component.scss',
  imports: [MatTableModule, MatPaginatorModule, MatSortModule, MatIconModule, CommonModule, ReactiveFormsModule, MatFormFieldModule, MatInputModule, MatProgressSpinnerModule],
})
export class ResultsComponent implements AfterViewInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<BenchmarkingResultsItem>;


  constructor(private benchmarkingService: BenchmarkingService) {}

  dataSource = new ResultsDataSource(this.benchmarkingService);
  searchControl = new FormControl('');


  /** Columns displayed in the table. Columns IDs can be added, removed, or reordered. */
  displayedColumns = [
    'id', 'ids_name', 'dataset_name', 'ensembling_method', 'start_time', 'stop_time', 'runtime', 
    'detection_rate', 'fpr', 'fnr', 'fdr', 'acc', 'prec', 'f1_score'];

  ngAfterViewInit(): void {
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }


  applyFilter(value: string) {
    this.dataSource.setFilter(value);
  }
  applyFilters(value: string) {
    this.dataSource.setFilter(value);
  }

  onKeyInput() {
    this.searchControl.valueChanges.subscribe(value => {
      console.log("Filtering with value: ", value);
    })
  }

}
