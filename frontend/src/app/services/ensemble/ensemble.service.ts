import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Observable, shareReplay, tap } from 'rxjs';
import { Ensemble, EnsembleContainer, EnsembleSetupData, EnsembleTechnique, EnsembleUpdateData } from '../../models/ensemble';
import { NetworkAnalysisData, StaticAnalysisData, stop_analysisData } from '../../models/analysis';

@Injectable({
  providedIn: 'root'
})
export class EnsembleService {
  private allTechniques$?: Observable<EnsembleTechnique[]>;

  constructor(
    private http: HttpClient
  ) { }

 // TODO 10: update all endpoints to use httpResponse objects instead of the other bullshit

  getAllTechnqiues(forceRefresh = false): Observable<EnsembleTechnique[]>{
    let path = "/crud/ensemble/technique/all"

    if (forceRefresh || !this.allTechniques$) {
      this.allTechniques$ = this.http.get<EnsembleTechnique[]>(environment.backendUrl+path)
        .pipe(shareReplay(1));
    }

    return this.allTechniques$;

  }

  getAllEnsembles(): Observable<Ensemble[]> {
    let path = "/crud/ensemble/all"
    return this.http.get<Ensemble[]>(environment.backendUrl+path);
  }

  sendEnsembleData(ensembleData: EnsembleSetupData) : Observable<HttpResponse<any>>{
    let path="/ensemble/setup"
    return this.http.post<any>(environment.backendUrl+path, ensembleData, { observe: 'response' })
  }

  updateEnsemble(ensemble: EnsembleUpdateData): Observable<HttpResponse<any>>{
    let path = "/crud/ensemble"
    return this.http.patch<EnsembleUpdateData>(environment.backendUrl+path, ensemble, { observe: 'response' });
  }

  removeEnsemble(ensembleToRemove: Ensemble) : Observable<HttpResponse<any>>{
    let path="/ensemble/remove/"
    return this.http.delete<Ensemble>(environment.backendUrl+path+ensembleToRemove.id, { observe: 'response' });
  }

  getEnsembleContainers(): Observable<EnsembleContainer[]>{
    let path = "/crud/ensemble/container/all";
    return this.http.get<EnsembleContainer[]>(environment.backendUrl+path);
  }

  start_static_analysis(staticAnalysisData: StaticAnalysisData) : Observable<HttpResponse<any>>{
    let path = "/ensemble/analysis/static";
    return this.http.post<HttpResponse<any>>(environment.backendUrl+path, staticAnalysisData, { observe: 'response' });
  }

  start_network_analysis(networkAnalysisData: NetworkAnalysisData): Observable<HttpResponse<any>>{
    let path = "/ensemble/analysis/network";
    return this.http.post<HttpResponse<any>>(environment.backendUrl+path, networkAnalysisData, { observe: 'response' });
  }

  stop_analysis(stopData: stop_analysisData): Observable<HttpResponse<any>>{
    let path = "/ensemble/analysis/stop";
    return this.http.post<any>(environment.backendUrl+path, stopData, { observe: 'response' });
  }

  invalidateTechniquesCache(): void {
    this.allTechniques$ = undefined;
  }

}
