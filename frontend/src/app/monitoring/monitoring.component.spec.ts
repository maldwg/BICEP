import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { MonitoringComponent } from './monitoring.component';
import { MetricsService, HistoricalMetricsData } from '../services/monitoring/metrics.service';

describe('MonitoringComponent', () => {
  let component: MonitoringComponent;
  let fixture: ComponentFixture<MonitoringComponent>;
  let metricsService: jasmine.SpyObj<MetricsService>;

  beforeEach(async () => {
    metricsService = jasmine.createSpyObj<MetricsService>('MetricsService', [
      'getCurrentMetrics',
      'getHistoricalMetrics'
    ]);
    metricsService.getCurrentMetrics.and.returnValue(of([]));
    metricsService.getHistoricalMetrics.and.returnValue(of({}));

    await TestBed.configureTestingModule({
      imports: [MonitoringComponent],
      providers: [
        { provide: MetricsService, useValue: metricsService }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(MonitoringComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('Timeline Alignment', () => {
    it('should align containers with different start times on common timeline', () => {
      // Container 1 started at t=1000, Container 2 started at t=1030 (30s later)
      const mockData: HistoricalMetricsData = {
        'container-1': {
          id: 1,
          timestamps: [1000, 1015, 1030, 1045, 1060], // Every 15s
          cpu: [0.5, 0.6, 0.7, 0.8, 0.9],
          memory: [100, 110, 120, 130, 140]
        },
        'container-2': {
          id: 2,
          timestamps: [1030, 1045, 1060], // Started at 1030
          cpu: [0.3, 0.4, 0.5],
          memory: [50, 60, 70]
        }
      };

      component.loadHistoricalDataToCharts(mockData);

      // Check timeline labels (should be common for all containers)
      expect(component.timeLabels.length).toBe(5); // 5 time points total

      // Check container-1 data (has data for all 5 points)
      const cpu1 = component.cpuHistory.get('container-1');
      expect(cpu1).toEqual([0.5, 0.6, 0.7, 0.8, 0.9]);

      // Check container-2 data (should have null for first 2 points, then data)
      const cpu2 = component.cpuHistory.get('container-2');
      expect(cpu2).toEqual([null, null, 0.3, 0.4, 0.5] as (number | null)[]);

      const mem2 = component.memoryHistory.get('container-2');
      expect(mem2).toEqual([null, null, 50, 60, 70] as (number | null)[]);
    });

    it('should handle containers starting at same time', () => {
      const mockData: HistoricalMetricsData = {
        'container-1': {
          id: 1,
          timestamps: [1000, 1015, 1030],
          cpu: [0.5, 0.6, 0.7],
          memory: [100, 110, 120]
        },
        'container-2': {
          id: 2,
          timestamps: [1000, 1015, 1030],
          cpu: [0.3, 0.4, 0.5],
          memory: [50, 60, 70]
        }
      };

      component.loadHistoricalDataToCharts(mockData);

      // Both should have data for all points (no nulls)
      const cpu1 = component.cpuHistory.get('container-1');
      expect(cpu1).toEqual([0.5, 0.6, 0.7]);

      const cpu2 = component.cpuHistory.get('container-2');
      expect(cpu2).toEqual([0.3, 0.4, 0.5]);
    });

    it('should use absolute timestamps for time labels', () => {
      const mockData: HistoricalMetricsData = {
        'container-1': {
          id: 1,
          timestamps: [1702300000, 1702300015], // Absolute Unix timestamps
          cpu: [0.5, 0.6],
          memory: [100, 110]
        }
      };

      component.loadHistoricalDataToCharts(mockData);

      // Time labels should be formatted from absolute timestamps
      expect(component.timeLabels.length).toBe(2);
      expect(component.timeLabels[0]).toContain(':'); // Should be time string like "10:00:00"
    });

    it('should handle empty data gracefully', () => {
      const mockData: HistoricalMetricsData = {};

      component.loadHistoricalDataToCharts(mockData);

      expect(component.timeLabels.length).toBe(0);
      expect(component.cpuHistory.size).toBe(0);
      expect(component.memoryHistory.size).toBe(0);
    });

    it('should fill gaps for containers with missing middle data points', () => {
      const mockData: HistoricalMetricsData = {
        'container-1': {
          id: 1,
          timestamps: [1000, 1015, 1030, 1045, 1060],
          cpu: [0.5, 0.6, 0.7, 0.8, 0.9],
          memory: [100, 110, 120, 130, 140]
        },
        'container-2': {
          id: 2,
          timestamps: [1000, 1060], // Missing middle points
          cpu: [0.3, 0.5],
          memory: [50, 70]
        }
      };

      component.loadHistoricalDataToCharts(mockData);

      // Container-2 should have nulls for missing timestamps
      const cpu2 = component.cpuHistory.get('container-2');
      expect(cpu2?.length).toBe(5);
      expect(cpu2?.[0]).toBe(0.3); // First point
      expect(cpu2?.[1]).toBeNull(); // Missing
      expect(cpu2?.[2]).toBeNull(); // Missing
      expect(cpu2?.[3]).toBeNull(); // Missing
      expect(cpu2?.[4]).toBe(0.5); // Last point
    });

    it('should keep top-level CIDS separate from expanded component series', () => {
      const mockData: HistoricalMetricsData = {
        'Hamstring-39021': {
          id: 12,
          timestamps: [1000, 1015],
          cpu: [1.1, 1.3],
          memory: [256, 300],
          type: 'CIDS',
          is_component: false
        },
        'Hamstring-39021 :: detector': {
          id: 1201,
          timestamps: [1000, 1015],
          cpu: [0.4, 0.5],
          memory: [80, 84],
          is_component: true,
          parent_id: 12,
          parent_name: 'Hamstring-39021',
          role: 'detector'
        }
      };

      component.loadHistoricalDataToCharts(mockData);

      expect(component.topLevelContainers.map(container => container.name)).toEqual(['Hamstring-39021']);
      expect(component.cidsContainers.map(container => container.name)).toEqual(['Hamstring-39021']);
      expect(component.containers.map(container => container.name)).toEqual([
        'Hamstring-39021',
        'Hamstring-39021 :: detector'
      ]);
    });

    it('should request expanded component series when toggling a CIDS', () => {
      metricsService.getHistoricalMetrics.calls.reset();

      component.toggleCidsComponents({
        id: 12,
        name: 'Hamstring-39021',
        status: 'active',
        cpu_usage: 0,
        memory_usage: 0,
        type: 'CIDS'
      });

      expect(component.isCidsExpanded(12)).toBeTrue();
      expect(metricsService.getHistoricalMetrics).toHaveBeenCalledWith('5m', undefined, '2s', [12]);
    });

    it('should collapse all expanded CIDS with one action', () => {
      component.expandedCidsIds.add(12);
      component.expandedCidsIds.add(13);
      metricsService.getHistoricalMetrics.calls.reset();

      component.showOverallOnly();

      expect(component.hasExpandedCids).toBeFalse();
      expect(metricsService.getHistoricalMetrics).toHaveBeenCalledWith('5m', undefined, '2s', []);
    });
  });
});
