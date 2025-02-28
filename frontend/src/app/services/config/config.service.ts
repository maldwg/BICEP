import { Injectable } from '@angular/core';
import { Configuration, ConfigurationSetupData, SerializedConfiguration } from '../../models/configuration';
import { HttpClient, HttpResponse } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Observable, finalize, map } from 'rxjs';
import { ContainerSetupData } from '../../models/container';
import { config } from 'process';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {

  constructor(
    private http: HttpClient
  ) { }

  


  getAllConfigurations(): Observable<Configuration[]> {
    let path = "/crud/configuration/all";
    return this.http.get<SerializedConfiguration[]>(environment.backendUrl + path).pipe(
      map(serializedConfigs => serializedConfigs.map(serializedConfig => this.deserializeConfiguration(serializedConfig)))
    );
  }

  getAllConfigurationsByType(fileType: string): Observable<Configuration[]> {
    let path = "/crud/configuration/all/" + fileType;
    return this.http.get<SerializedConfiguration[]>(environment.backendUrl + path).pipe(
      map(serializedConfigs => serializedConfigs.map(serializedConfig => this.deserializeConfiguration(serializedConfig)))
    );
  }

  getAllFileTypes(): Observable<string[]>{
    let path = "/crud/configuration/file-types";
    return this.http.get<string[]>(environment.backendUrl+path);
  }

  removeConfiguration(id: number): Observable<HttpResponse<any>> {
    let path = "/crud/configuration/";
    return this.http.delete<HttpResponse<any>>(environment.backendUrl+path+id, { observe: 'response' });
  }

  addConfiguration(configuration: ConfigurationSetupData){
    let path = "/crud/configuration/add"
    const formData = new FormData();
    formData.append("name", configuration.name);
    formData.append("description", configuration.description);
    formData.append('configuration', configuration.configuration, configuration.configuration.name);
    formData.append("file_type", configuration.file_type);
    return this.http.post(environment.backendUrl+path, formData, {
      reportProgress: true,
      observe: "events"
    });
  }



  deserializeConfiguration(serializedConfig: SerializedConfiguration): Configuration {
    return {
      id: serializedConfig.id,
      name: serializedConfig.name,
      configuration: atob(serializedConfig.configuration), // Decode Base64 to binary
      file_type: serializedConfig.file_type,
      description: serializedConfig.description
    };
  }

}
