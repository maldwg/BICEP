import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';
import { Ensemble, EnsembleContainer, EnsembleSetupData, EnsembleTechnqiue, EnsembleUpdateData } from '../../models/ensemble';
import { NetworkAnalysisData, StaticAnalysisData, StopAnalysisData } from '../../models/analysis';

@Injectable({
  providedIn: 'root'
})
export class EnsembleService {

  constructor(
    private http: HttpClient
  ) { }

 // TODO: update all endpoints to use httpResponse objects instead of the other bullshit

  getAllTechnqiues(): Observable<EnsembleTechnqiue[]>{
    let path = "/crud/ensemble/technique/all"
    return this.http.get<EnsembleTechnqiue[]>(environment.backendUrl+path);

  }

  getAllEnsembles(): Observable<Ensemble[]> {
    let path = "/crud/ensemble/all"
    return this.http.get<Ensemble[]>(environment.backendUrl+path);
  }

  sendEnsembleData(ensembleData: EnsembleSetupData) : Observable<EnsembleSetupData>{
    let path="/ensemble/setup"
    return this.http.post<EnsembleSetupData>(environment.backendUrl+path, ensembleData)
  }

  updateEnsemble(ensemble: EnsembleUpdateData): Observable<EnsembleUpdateData>{
    let path = "/crud/ensemble"
    return this.http.patch<EnsembleUpdateData>(environment.backendUrl+path, ensemble);
  }

  removeEnsemble(ensembleToRemove: Ensemble) : Observable<Ensemble>{
    let path="/ensemble/remove/"
    return this.http.delete<Ensemble>(environment.backendUrl+path+ensembleToRemove.id);
  }

  getEnsembleContainers(): Observable<EnsembleContainer[]>{
    let path = "/crud/ensemble/container/all";
    return this.http.get<EnsembleContainer[]>(environment.backendUrl+path);
  }

  startStaticAnalysis(staticAnalysisData: StaticAnalysisData) : Observable<HttpResponse<any>>{
    let path = "/ensemble/analysis/static";
    return this.http.post<HttpResponse<any>>(environment.backendUrl+path, staticAnalysisData, { observe: 'response' });
  }

  startNetworkAnalysis(networkAnalysisData: NetworkAnalysisData): Observable<HttpResponse<any>>{
    let path = "/ensemble/analysis/network";
    return this.http.post<HttpResponse<any>>(environment.backendUrl+path, networkAnalysisData, { observe: 'response' });
  }

  stopAnalysis(stopData: StopAnalysisData): Observable<HttpResponse<any>>{
    let path = "/ensemble/analysis/stop";
    return this.http.post<any>(environment.backendUrl+path, stopData, { observe: 'response' });
  }

}
