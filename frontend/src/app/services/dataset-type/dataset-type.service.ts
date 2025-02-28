import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DatasetType } from '../../models/datasetType';

@Injectable({
  providedIn: 'root'
})
export class DatasetTypesService {

  constructor(
    private http: HttpClient
  ) { }


getAllDatasetTypes(): Observable<DatasetType[]>{
  let path = "/crud/dataset-type/all";
  return this.http.get<DatasetType[]>(environment.backendUrl+path)
}

}