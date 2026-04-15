import { HttpClient, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, shareReplay, tap } from 'rxjs';
import { DockerHostSystem, DockerHostSystemCreationData } from '../../models/host';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class DockerHostService {
  private allHosts$?: Observable<DockerHostSystem[]>;

  constructor(
    private http: HttpClient,
  ) { }


  getAllHosts(
    forceRefresh = false,
  ): Observable<DockerHostSystem[]> {
    const path = '/crud/host/all';

    if (forceRefresh || !this.allHosts$) {
      this.allHosts$ = this.http.get<DockerHostSystem[]>(
        environment.backendUrl + path,
      )
        .pipe(shareReplay(1));
    }

    return this.allHosts$;
  }

  addHost(hostData: DockerHostSystemCreationData): Observable<HttpResponse<any>> {
    let path = "/crud/host/add"
    return this.http.post<HttpResponse<any>>(environment.backendUrl + path, hostData, { observe: 'response' })
      .pipe(
        tap(() => this.invalidateHostCache())
      );
  }

  removeHost(hostId: number): Observable<HttpResponse<any>> {
    let path = "/crud/host/delete/"
    return this.http.delete<HttpResponse<any>>(environment.backendUrl + path + hostId, { observe: 'response' })
      .pipe(
        tap(() => this.invalidateHostCache())
      );
  }

  invalidateHostCache(): void {
    this.allHosts$ = undefined;
  }

}
