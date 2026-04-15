import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, shareReplay, tap } from 'rxjs';
import { Dataset, DatasetSetupData } from '../../models/dataset';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class DatasetService {
  private allDatasets$?: Observable<Dataset[]>;

  constructor(
    private http: HttpClient,

  ) { }


  getAllDatasets(forceRefresh = false): Observable<Dataset[]> {
    let path = "/crud/dataset/all";

    if (forceRefresh || !this.allDatasets$) {
      this.allDatasets$ = this.http.get<Dataset[]>(environment.backendUrl + path)
        .pipe(shareReplay(1));
    }

    return this.allDatasets$;
  }

  removeDataset(id: number): Observable<HttpResponse<any>> {
    let path = "/crud/dataset/";
    return this.http.delete<HttpResponse<any>>(environment.backendUrl+path+id, {observe: "response"})
      .pipe(
        tap(() => this.invalidateDatasetsCache())
      );
  }

  addDataset(dataset: DatasetSetupData): Observable<HttpEvent<any>>{
    let path = "/crud/dataset/add"
    const formData = new FormData();
    formData.append("name", dataset.name);
    formData.append("description", dataset.description);
    formData.append('data_file', dataset.data_file, dataset.data_file.name)
    formData.append('labels_file', dataset.labels_file, dataset.labels_file.name)
    formData.append('dataset_type_id', dataset.dataset_type_id)

    return this.http.post(environment.backendUrl+path, formData, {
      reportProgress: true,
      observe: "events"
    }).pipe(
      tap((event) => {
        if (event.type === HttpEventType.Response) {
          this.invalidateDatasetsCache();
        }
      })
    );
  }

  invalidateDatasetsCache(): void {
    this.allDatasets$ = undefined;
  }
}
