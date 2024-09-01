import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, finalize, map } from 'rxjs';
import { Dataset, DatasetSetupData, SerializedDataset } from '../../models/dataset';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class DatasetService {

  constructor(
    private http: HttpClient,

  ) { }



  getAllDatasets(): Observable<Dataset[]> {
    let path = "/crud/dataset/all";
    return this.http.get<SerializedDataset[]>(environment.backendUrl + path).pipe(
      map((serializedDatasets) => serializedDatasets.map(serializedDataset => this.deserializeConfiguration(serializedDataset)))
    );
  }

  removeDataset(id: number) {
    let path = "/crud/dataset/";
    return this.http.delete(environment.backendUrl+path+id);
  }

  addDataset(dataset: DatasetSetupData){
    let path = "/crud/dataset/add"
    const formData = new FormData();
    formData.append("name", dataset.name);
    formData.append("description", dataset.description);
    for (var file of dataset.configuration) {
      formData.append('configuration', file, file.name);
    };    
    return this.http.post(environment.backendUrl+path, formData, {
      reportProgress: true,
      observe: "events"
    });
  }



  deserializeConfiguration(serializedDataset: SerializedDataset): Dataset {
    return {
      id: serializedDataset.id,
      name: serializedDataset.name,
      pcap_file_path: serializedDataset.pcap_file_path,
      labels_file_path: serializedDataset.labels_file_path, 
      description: serializedDataset.description,
      ammount_benign: serializedDataset.ammount_benign,
      ammount_malicious: serializedDataset.ammount_malicious
    };
  }


}
