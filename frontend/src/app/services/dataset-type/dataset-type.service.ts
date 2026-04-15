import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DatasetType } from '../../models/datasetType';

@Injectable({
  providedIn: 'root'
})
export class DatasetTypesService {
  private allDatasetTypes$?: Observable<DatasetType[]>;

  constructor(
    private http: HttpClient
  ) { }


  getAllDatasetTypes(forceRefresh = false): Observable<DatasetType[]> {
    let path = "/crud/dataset-type/all";

    if (forceRefresh || !this.allDatasetTypes$) {
      this.allDatasetTypes$ = this.http.get<DatasetType[]>(environment.backendUrl+path)
        .pipe(shareReplay(1));
    }

    return this.allDatasetTypes$;
  }

}
