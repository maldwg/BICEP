import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { DockerHostSystem, DockerHostSystemCreationData } from '../../models/host';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class DockerHostService {

  constructor(
    private http: HttpClient,
  ) { }


getAllHosts(): Observable<DockerHostSystem[]>{
  let path = "/crud/host/all"
  return this.http.get<DockerHostSystem[]>(environment.backendUrl + path)
}

addHost(hostData: DockerHostSystemCreationData): Observable<HttpResponse<any>>{
  let path = "/crud/host/add"
  return this.http.post<HttpResponse<any>>(environment.backendUrl + path, hostData, { observe: 'response' })
}

removeHost(hostId: number): Observable<HttpResponse<any>>{
  let path = "/crud/host/delete/"
  return this.http.delete<HttpResponse<any>>(environment.backendUrl + path + hostId, { observe: 'response' })
}


}
