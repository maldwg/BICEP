import { Injectable } from '@angular/core';
import { IdsTool } from '../../models/ids';
import { Container, ContainerSetupData, ContainerUpdateData } from '../../models/container';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { __param } from 'tslib';
import { NetworkAnalysisData, StaticAnalysisData, StopAnalysisData } from '../../models/analysis';

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

  startStaticAnalysis(staticAnalysisData: StaticAnalysisData) : Observable<StaticAnalysisData>{
    let path = "/ids/analysis/static";
    return this.http.post<StaticAnalysisData>(environment.backendUrl+path, staticAnalysisData);
  }

  startNetworkAnalysis(networkAnalysisData: NetworkAnalysisData){
    let path = "/ids/analysis/network";
    return this.http.post<StaticAnalysisData>(environment.backendUrl+path, networkAnalysisData);
  }

  stopAnalysis(stopData: StopAnalysisData){
    let path = "/ids/analysis/stop";
    return this.http.post(environment.backendUrl+path, stopData);
  }
}
