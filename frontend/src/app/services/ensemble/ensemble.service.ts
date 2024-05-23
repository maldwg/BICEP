import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';
import { Ensemble, EnsembleSetupData, EnsembleTechnqiue } from '../../models/ensemble';

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

  removeEnsemble(ensembleToRemove: Ensemble) : Observable<Ensemble>{
    let path="/ensemble/remove/"
    return this.http.delete<Ensemble>(environment.backendUrl+path+ensembleToRemove.id);
  }

}
