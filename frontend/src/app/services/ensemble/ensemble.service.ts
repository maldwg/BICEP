import { HttpClient } from '@angular/common/http';
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

  startStaticAnalysis(staticAnalysisData: StaticAnalysisData) : Observable<StaticAnalysisData>{
    let path = "/ensemble/analysis/static";
    return this.http.post<StaticAnalysisData>(environment.backendUrl+path, staticAnalysisData);
  }

  startNetworkAnalysis(networkAnalysisData: NetworkAnalysisData){
    let path = "/ensemble/analysis/network";
    return this.http.post<NetworkAnalysisData>(environment.backendUrl+path, networkAnalysisData);
  }

  stopAnalysis(stopData: StopAnalysisData){
    let path = "/ensemble/analysis/stop";
    return this.http.post(environment.backendUrl+path, stopData);
  }

}
