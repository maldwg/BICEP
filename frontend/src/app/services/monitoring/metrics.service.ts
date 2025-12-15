import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface ContainerMetric {
    id: number;
    name: string;
    status: string;
    cpu_usage: number;
    memory_usage: number;
}

export interface HistoricalMetricsData {
    [containerName: string]: {
        id: number;
        timestamps: number[];
        cpu: number[];
        memory: number[];
    };
}

@Injectable({
    providedIn: 'root'
})
export class MetricsService {
    private readonly baseUrl = `${environment.backendUrl}/monitoring`;

    constructor(private http: HttpClient) { }

    /**
     * Fetch current real-time metrics for all containers
     */
    getCurrentMetrics(): Observable<ContainerMetric[]> {
        return this.http.get<{ content: ContainerMetric[] }>(`${this.baseUrl}/metrics`)
            .pipe(
                map(response => response.content)
            );
    }

    /**
     * Fetch historical metrics with time range
     * @param start - Start time (e.g., '15m', '1h' or ISO timestamp)
     * @param end - End time (ISO timestamp, optional)
     * @param step - Data point interval (default: '15s')
     */
    getHistoricalMetrics(
        start: string,
        end?: string,
        step: string = '15s'
    ): Observable<HistoricalMetricsData> {
        let params = new HttpParams()
            .set('start', start)
            .set('step', step);

        if (end) {
            params = params.set('end', end);
        }

        return this.http.get<{ content: HistoricalMetricsData }>(
            `${this.baseUrl}/metrics/historical`,
            { params }
        ).pipe(
            map(response => response.content)
        );
    }
}
