import { Injectable } from '@angular/core';
import { Configuration } from '../../models/configuration';
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

}
