import { Injectable } from '@angular/core';
import { DataSource } from '@angular/cdk/collections';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { catchError, map, startWith, switchMap } from 'rxjs/operators';
import { Observable, of as observableOf, merge, BehaviorSubject, of } from 'rxjs';
import {
  BenchmarkingJob,
  BenchmarkJobCreate,
  BenchmarkingJobResponse,
  BenchmarkingJobsResponse,
  BenchmarkingResultsItem
} from '../../models/benchmarking';
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

    createBenchmarkingJob(job: BenchmarkJobCreate): Observable<BenchmarkingJobResponse> {
      const path = "/benchmarking/jobs";
      return this.http.post<BenchmarkingJobResponse>(environment.backendUrl + path, job);
    }

    getBenchmarkingJobs(limit = 20): Observable<BenchmarkingJobsResponse> {
      const path = `/benchmarking/jobs?limit=${limit}`;
      return this.http.get<BenchmarkingJobsResponse>(environment.backendUrl + path);
    }

    stopBenchmarkingJob(jobId: number): Observable<BenchmarkingJobResponse> {
      const path = `/benchmarking/jobs/${jobId}/stop`;
      return this.http.post<BenchmarkingJobResponse>(environment.backendUrl + path, {});
    }
}
