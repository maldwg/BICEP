import { Injectable } from '@angular/core';
import { Configuration, ConfigurationSetupData, SerializedConfiguration, DeserializedConfiguration } from '../../models/configuration';
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

  

// rewrite both to not use deserialized configuration 
// thenj use these methods to 
  getAllConfigurations(): Observable<Configuration[]> {
    let path = "/crud/configuration/all";
    return this.http.get<Configuration[]>(environment.backendUrl + path);
  }

  getAllConfigurationsByType(fileType: string): Observable<Configuration[]> {
    let path = "/crud/configuration/all/" + fileType;
    return this.http.get<Configuration[]>(environment.backendUrl + path);
    //.pipe(
      //map(serializedConfigs => serializedConfigs.map(serializedConfig => this.deserializeConfiguration(serializedConfig)))
    //);
  }

  getDeserializedConfiguration(id: number): Observable<DeserializedConfiguration> {
    const path = `/crud/configuartion/${id}/serialized`;
    return this.http.get<SerializedConfiguration>(environment.backendUrl + path).pipe(
      map(serialized => this.deserializeConfiguration(serialized))
    );
  }

// TODO add service point for deserialized get for each config

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



  deserializeConfiguration(serializedConfig: SerializedConfiguration): DeserializedConfiguration {
    return {
      id: serializedConfig.id,
      name: serializedConfig.name,
      file_content: atob(serializedConfig.file_content), // Decode Base64 to binary
      file_path: serializedConfig.file_path,
      file_type: serializedConfig.file_type,
      description: serializedConfig.description
    };
  }

}
