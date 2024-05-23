import { Injectable } from '@angular/core';
import { IdsTool } from '../../models/ids';
import { Container, ContainerSetupData } from '../../models/container';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class IdsService {

  constructor(
    private http: HttpClient
  ) { }

  
  getContainers(): void{

  }

  sendContainerSetupData(containerData: ContainerSetupData): Observable<ContainerSetupData>{
    let path = "/ids/setup";
    console.log("send data")
    return this.http.post<ContainerSetupData>(environment.backendUrl+path, containerData);
  }

  getAllIdsTools(): Observable<IdsTool[]> {
    let path = "/crud/ids-tool/all";
    return this.http.get<IdsTool[]>(environment.backendUrl+path);
  }

  getAllIdsContainer(): Observable<Container[]>{
    let path = "/crud/container/all"
    return this.http.get<Container[]>(environment.backendUrl+path);
  }

  removeContainerById(id: number) {
    let path = "/ids/remove/";
    return this.http.delete(environment.backendUrl+path+id);
  }
}
