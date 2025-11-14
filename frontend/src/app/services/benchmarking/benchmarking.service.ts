import { Injectable } from '@angular/core';
import { DataSource } from '@angular/cdk/collections';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { catchError, map, startWith, switchMap } from 'rxjs/operators';
import { Observable, of as observableOf, merge, BehaviorSubject, of } from 'rxjs';
import { BenchmarkingResultsItem } from '../../models/benchmarking';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class BenchmarkingService {
  
  constructor(
    private http: HttpClient
  ) { }

    getAllConfigurations(): Observable<BenchmarkingResultsItem[]> {
      let path = "/crud/benchmarking-results/all";
      return this.http.get<BenchmarkingResultsItem[]>(environment.backendUrl + path);
    }
}