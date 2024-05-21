import { Injectable } from '@angular/core';
import { Configuration, ConfigurationSetupData } from '../../models/configuration';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';

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

  removeConfiguration(id: number) {
    let path = "/crud/configuration/";
    this.http.delete(environment.backendUrl+path+id);
  }

  addConfiguration(configuration: ConfigurationSetupData): Observable<ConfigurationSetupData>{
    let path = "/crud/configuration/add"
    return this.http.post<ConfigurationSetupData>(environment.backendUrl+path, configuration);
  }

}
