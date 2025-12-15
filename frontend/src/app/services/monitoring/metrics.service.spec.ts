import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { MetricsService } from './metrics.service';
import { environment } from '../../../environments/environment';

describe('MetricsService', () => {
    let service: MetricsService;
    let httpMock: HttpTestingController;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            providers: [MetricsService]
        });
        service = TestBed.inject(MetricsService);
        httpMock = TestBed.inject(HttpTestingController);
    });

    afterEach(() => {
        httpMock.verify();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('getCurrentMetrics', () => {
        it('should fetch current metrics from backend', () => {
            const mockResponse = {
                content: [
                    { id: 1, name: 'container-1', cpu_usage: 0.5, memory_usage: 256.5, status: 'active' }
                ]
            };

            service.getCurrentMetrics().subscribe(metrics => {
                expect(metrics.length).toBe(1);
                expect(metrics[0].name).toBe('container-1');
                expect(metrics[0].cpu_usage).toBe(0.5);
            });

            const req = httpMock.expectOne(`${environment.backendUrl}/monitoring/metrics`);
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
        });

        it('should handle errors gracefully', () => {
            service.getCurrentMetrics().subscribe({
                next: () => fail('should have failed'),
                error: (error) => {
                    expect(error).toBeTruthy();
                }
            });

            const req = httpMock.expectOne(`${environment.backendUrl}/monitoring/metrics`);
            req.error(new ProgressEvent('Network error'));
        });
    });

    describe('getHistoricalMetrics', () => {
        it('should fetch historical metrics with time range', () => {
            const mockResponse = {
                content: {
                    'container-1': {
                        id: 1,
                        timestamps: [1000, 1015, 1030],
                        cpu: [0.5, 0.6, 0.7],
                        memory: [256, 257, 258]
                    }
                }
            };

            service.getHistoricalMetrics('15m').subscribe(data => {
                expect(data['container-1']).toBeDefined();
                expect(data['container-1'].timestamps.length).toBe(3);
            });

            const req = httpMock.expectOne(req =>
                req.url === `${environment.backendUrl}/monitoring/metrics/historical` &&
                req.params.get('start') === '15m'
            );
            expect(req.request.method).toBe('GET');
            req.flush(mockResponse);
        });

        it('should support custom time range with start and end', () => {
            const start = '2025-12-12T10:00:00Z';
            const end = '2025-12-12T11:00:00Z';

            service.getHistoricalMetrics(start, end).subscribe();

            const req = httpMock.expectOne(req =>
                req.url === `${environment.backendUrl}/monitoring/metrics/historical` &&
                req.params.get('start') === start &&
                req.params.get('end') === end
            );
            req.flush({ content: {} });
        });

        it('should use default step of 15s', () => {
            service.getHistoricalMetrics('1h').subscribe();

            const req = httpMock.expectOne(req =>
                req.params.get('step') === '15s'
            );
            req.flush({ content: {} });
        });
    });
});
