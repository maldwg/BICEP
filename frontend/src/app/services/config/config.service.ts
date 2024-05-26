import { Injectable } from '@angular/core';
import { Configuration, ConfigurationSetupData } from '../../models/configuration';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';
import { ContainerSetupData } from '../../models/container';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {

  constructor(
    private http: HttpClient
  ) { }

  

  getAllConfigurations(): Observable<Configuration[]>{
    let path = "/crud/configuration/all";
    return this.http.get<Configuration[]>(environment.backendUrl+path);
  }

  getAllConfigurationsByType(fileType: string): Observable<Configuration[]>{
    let path = "/crud/configuration/all/"+fileType;
    return this.http.get<Configuration[]>(environment.backendUrl+path);
  }

  getAllFileTypes(): Observable<string[]>{
    let path = "/crud/configuration/file-types";
    return this.http.get<string[]>(environment.backendUrl+path);
  }

  removeConfiguration(id: number) {
    let path = "/crud/configuration/";
    return this.http.delete(environment.backendUrl+path+id);
  }

  addConfiguration(configuration: ConfigurationSetupData): Observable<ConfigurationSetupData>{
    let path = "/crud/configuration/add"
    const formData = new FormData();
    formData.append("name", configuration.name);
    formData.append("description", configuration.description);
    formData.append("configuration", configuration.configuration);
    formData.append("file_type", configuration.file_type);
    return this.http.post<ConfigurationSetupData>(environment.backendUrl+path, formData);
  }

}
