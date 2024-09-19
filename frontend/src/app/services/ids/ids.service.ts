import { Injectable } from '@angular/core';
import { IdsTool } from '../../models/ids';
import { Container, ContainerSetupData, ContainerUpdateData } from '../../models/container';
import { HttpClient, HttpErrorResponse, HttpParams, HttpResponse } from '@angular/common/http';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { __param } from 'tslib';
import { NetworkAnalysisData, StaticAnalysisData, stop_analysisData } from '../../models/analysis';

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

  updateContainer(container: ContainerUpdateData): Observable<ContainerUpdateData>{
    let path = "/crud/container"
    return this.http.patch<ContainerUpdateData>(environment.backendUrl+path, container);
  }

  getAllIdsTools(): Observable<IdsTool[]> {
    let path = "/crud/ids-tool/all";
    return this.http.get<IdsTool[]>(environment.backendUrl+path);
  }

  getAllIdsContainer(): Observable<Container[]>{
    let path = "/crud/container/all"
    return this.http.get<Container[]>(environment.backendUrl+path);
  }

  getAllNonEnsembledIdsContainer(): Observable<Container[]>{
    let path = "/crud/container/without/ensemble"
    return this.http.get<Container[]>(environment.backendUrl+path);
  }

  removeContainerById(id: number) {
    let path = "/ids/remove/";
    return this.http.delete(environment.backendUrl+path+id);
  }

  start_static_analysis(staticAnalysisData: StaticAnalysisData) : Observable<HttpResponse<any>>{
    let path = "/ids/analysis/static";
    return this.http.post<HttpResponse<any>>(environment.backendUrl+path, staticAnalysisData, { observe: 'response' });
  }

  start_network_analysis(networkAnalysisData: NetworkAnalysisData): Observable<HttpResponse<any>>{
    let path = "/ids/analysis/network";
    return this.http.post<HttpResponse<any>>(environment.backendUrl+path, networkAnalysisData, { observe: 'response' });
  }

  stop_analysis(stopData: stop_analysisData): Observable<HttpResponse<any>>{
    let path = "/ids/analysis/stop";
    return this.http.post<HttpResponse<any>>(environment.backendUrl+path, stopData, { observe: 'response' });
  }
}
