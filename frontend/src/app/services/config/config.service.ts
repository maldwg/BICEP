import { Injectable } from '@angular/core';
import { Configuration, ConfigurationSetupData, SerializedConfiguration, DeserializedConfiguration } from '../../models/configuration';
import { HttpClient, HttpEvent, HttpEventType, HttpResponse } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Observable, map, shareReplay, tap } from 'rxjs';
import { ContainerSetupData, ComposeService } from '../../models/container';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private allConfigurations$?: Observable<Configuration[]>;
  private allFileTypes$?: Observable<string[]>;
  private readonly configurationsByTypeCache = new Map<string, Observable<Configuration[]>>();
  private readonly configurationServicesCache = new Map<number, Observable<ComposeService[]>>();

  constructor(
    private http: HttpClient
  ) { }


  getAllConfigurations(forceRefresh = false): Observable<Configuration[]> {
    let path = "/crud/configuration/all";

    if (forceRefresh || !this.allConfigurations$) {
      this.allConfigurations$ = this.http.get<Configuration[]>(environment.backendUrl + path)
        .pipe(shareReplay(1));
    }

    return this.allConfigurations$;
  }

  getAllConfigurationsByType(fileType: string, forceRefresh = false): Observable<Configuration[]> {
    let path = "/crud/configuration/all/" + fileType;

    if (forceRefresh || !this.configurationsByTypeCache.has(fileType)) {
      this.configurationsByTypeCache.set(
        fileType,
        this.http.get<Configuration[]>(environment.backendUrl + path).pipe(shareReplay(1))
      );
    }

    return this.configurationsByTypeCache.get(fileType)!;
  }

  getDeserializedConfiguration(id: number): Observable<DeserializedConfiguration> {
    const path = `/crud/configuartion/${id}/serialized`;
    return this.http.get<SerializedConfiguration>(environment.backendUrl + path).pipe(
      map(serialized => this.deserializeConfiguration(serialized))
    );
  }

  // TODO add service point for deserialized get for each config

  getAllFileTypes(forceRefresh = false): Observable<string[]> {
    let path = "/crud/configuration/file-types";

    if (forceRefresh || !this.allFileTypes$) {
      this.allFileTypes$ = this.http.get<string[]>(environment.backendUrl + path)
        .pipe(shareReplay(1));
    }

    return this.allFileTypes$;
  }

  removeConfiguration(id: number): Observable<HttpResponse<any>> {
    let path = "/crud/configuration/";
    return this.http.delete<HttpResponse<any>>(environment.backendUrl + path + id, { observe: 'response' })
      .pipe(
        tap(() => this.invalidateConfigurationCaches())
      );
  }

  addConfiguration(configuration: ConfigurationSetupData): Observable<HttpEvent<any>> {
    let path = "/crud/configuration/add"
    const formData = new FormData();
    formData.append("name", configuration.name);
    formData.append("description", configuration.description);
    formData.append('configuration', configuration.configuration, configuration.configuration.name);
    formData.append("file_type", configuration.file_type);
    return this.http.post(environment.backendUrl + path, formData, {
      reportProgress: true,
      observe: "events"
    }).pipe(
      tap((event) => {
        if (event.type === HttpEventType.Response) {
          this.invalidateConfigurationCaches();
        }
      })
    );
  }



  getConfigurationServices(id: number, forceRefresh = false): Observable<ComposeService[]> {
    let path = `/crud/configuration/${id}/services`;

    if (forceRefresh || !this.configurationServicesCache.has(id)) {
      this.configurationServicesCache.set(
        id,
        this.http.get<ComposeService[]>(environment.backendUrl + path).pipe(shareReplay(1))
      );
    }

    return this.configurationServicesCache.get(id)!;
  }

  deserializeConfiguration(serializedConfig: SerializedConfiguration): DeserializedConfiguration {
    return {
      id: serializedConfig.id,
      name: serializedConfig.name,
      file_content: atob(serializedConfig.file_content), // Decode Base64 to binary
      file_path: serializedConfig.file_path,
      file_type: serializedConfig.file_type,
      description: serializedConfig.description
    };
  }

  invalidateConfigurationCaches(): void {
    this.allConfigurations$ = undefined;
    this.allFileTypes$ = undefined;
    this.configurationsByTypeCache.clear();
    this.configurationServicesCache.clear();
  }

}
