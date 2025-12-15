import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxEchartsModule, NGX_ECHARTS_CONFIG } from 'ngx-echarts';
import { Subscription, interval } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { FormsModule } from '@angular/forms';
import { EChartsOption } from 'echarts';
import { MetricsService, ContainerMetric } from '../services/monitoring/metrics.service';
import { MatTooltipModule } from '@angular/material/tooltip';

// ContainerMetric now imported from MetricsService

@Component({
  selector: 'app-monitoring',
  standalone: true,
  imports: [CommonModule, NgxEchartsModule, MatCardModule, MatIconModule, MatButtonModule, MatSelectModule, MatFormFieldModule, MatInputModule, MatCheckboxModule, FormsModule, MatTooltipModule],
  templateUrl: './monitoring.component.html',
  styleUrl: './monitoring.component.scss',
  providers: [
    {
      provide: NGX_ECHARTS_CONFIG,
      useFactory: () => ({ echarts: () => import('echarts') })
    }
  ]
})
export class MonitoringComponent implements OnInit, OnDestroy {
  containers: ContainerMetric[] = [];
  pollingSubscription?: Subscription;

  // History for each container
  cpuHistory: Map<string, (number | null)[]> = new Map();
  memoryHistory: Map<string, (number | null)[]> = new Map();
  timeLabels: string[] = [];

  // Chart options
  cpuChartOption: EChartsOption = {};
  memoryChartOption: EChartsOption = {};

  // Chart instances for preserving selection
  private cpuChartInstance: any;
  private memoryChartInstance: any;

  // Time range settings
  selectedTimeRange: string = '5m';
  maxDataPoints: number = 60;
  pollingInterValSeconds = 5;

  // Custom time range
  customStartTime: string = '';
  customEndTime: string = '';
  useCustomRange: boolean = false;

  constructor(private metricsService: MetricsService) { }

  ngOnInit(): void {
    // Load historical data first
    this.loadHistoricalData();

    // Poll every 5 seconds - reload the full historical dataset
    // This ensures we get all 2s data points without timeline issues
    this.pollingSubscription = interval(this.pollingInterValSeconds * 1000)
      .subscribe(() => {
        if (!this.useCustomRange) {
          // Simply reload the complete historical data for selected range
          // This gets all 2s data points that containers pushed
          this.loadHistoricalData();
        }
      });
  }

  ngOnDestroy(): void {
    if (this.pollingSubscription) {
      this.pollingSubscription.unsubscribe();
    }
  }

  updateMetrics(newMetrics: ContainerMetric[]): void {
    const now = new Date();
    const timeStr = now.toLocaleTimeString();

    this.containers = newMetrics;
    this.timeLabels.push(timeStr);
    if (this.timeLabels.length > this.maxDataPoints) this.timeLabels.shift();

    newMetrics.forEach(container => {
      // Update CPU History
      if (!this.cpuHistory.has(container.name)) {
        this.cpuHistory.set(container.name, []);
      }
      const cpuHist = this.cpuHistory.get(container.name)!;
      cpuHist.push(container.cpu_usage);
      if (cpuHist.length > this.maxDataPoints) cpuHist.shift();

      // Update Memory History
      if (!this.memoryHistory.has(container.name)) {
        this.memoryHistory.set(container.name, []);
      }
      const memHist = this.memoryHistory.get(container.name)!;
      memHist.push(container.memory_usage);
      if (memHist.length > this.maxDataPoints) memHist.shift();
    });

    this.updateCharts();
  }

  onQuickRangeChange(): void {
    this.useCustomRange = false;
    this.customStartTime = '';
    this.customEndTime = '';

    // Update maxDataPoints based on selected time range
    // With 2s intervals: maxPoints = (minutes * 60) / 2
    switch (this.selectedTimeRange) {
      case '5m':
        this.maxDataPoints = (5 * 60) / 2; // 150 points
        break;
      case '15m':
        this.maxDataPoints = (15 * 60) / 2; // 450 points
        break;
      case '30m':
        this.maxDataPoints = (30 * 60) / 2; // 900 points
        break;
      case '1h':
        this.maxDataPoints = (60 * 60) / 2; // 1800 points
        break;
      case '3h':
        this.maxDataPoints = (180 * 60) / 2; // 5400 points
        break;
    }

    // Load fresh historical data for the new range
    this.loadHistoricalData();
  }

  onCustomTimeChange(): void {
    // Support flexible ranges:
    // - Both start and end: Range query
    // - Only start: From start to now
    // - Only end: Ignored (need start)
    // - Neither: Ignored
    if (this.customStartTime) {
      this.useCustomRange = true;
      this.selectedTimeRange = 'custom';
      this.loadHistoricalData();
    }
  }

  loadHistoricalData(): void {
    let start: string;
    let end: string | undefined;

    if (this.useCustomRange && this.customStartTime) {
      // Custom range: use provided times
      start = new Date(this.customStartTime).toISOString();
      end = this.customEndTime ? new Date(this.customEndTime).toISOString() : undefined;
    } else {
      // Quick range: use selected time range
      start = this.selectedTimeRange || '5m';
      end = undefined; // Backend defaults to 'now'
    }

    // Use 2s step to capture all container pushes (containers push every ~2s)
    this.metricsService.getHistoricalMetrics(start, end, '2s').subscribe({
      next: (data) => {
        this.loadHistoricalDataToCharts(data);
      },
      error: (error) => {
        console.error('Error loading historical data:', error);
        // If no historical data, keep monitoring
      }
    });
  }

  loadHistoricalDataToCharts(data: any): void {
    // Clear existing data
    this.cpuHistory.clear();
    this.memoryHistory.clear();
    this.timeLabels = [];

    // Extract container names
    const containerNames = Object.keys(data);

    if (containerNames.length === 0) return;

    // 1. Find the global time range across ALL containers
    let minTime = Infinity;
    let maxTime = 0;

    for (const containerName of containerNames) {
      const containerData = data[containerName];
      if (containerData.timestamps && containerData.timestamps.length > 0) {
        minTime = Math.min(minTime, containerData.timestamps[0]);
        maxTime = Math.max(maxTime, containerData.timestamps[containerData.timestamps.length - 1]);
      }
    }

    // If no valid data, return
    if (minTime === Infinity || maxTime === 0) return;

    // 2. Determine the time step from the first container with data
    let step = 15; // Default 15 seconds
    for (const containerName of containerNames) {
      const containerData = data[containerName];
      if (containerData.timestamps && containerData.timestamps.length >= 2) {
        step = containerData.timestamps[1] - containerData.timestamps[0];
        break;
      }
    }

    // 3. Create a common timeline
    const commonTimeline: number[] = [];
    for (let t = minTime; t <= maxTime; t += step) {
      commonTimeline.push(t);
    }

    // 4. Create time labels from common timeline
    this.timeLabels = commonTimeline.map(ts =>
      new Date(ts * 1000).toLocaleTimeString()
    );

    // 5. Map each container's data to the common timeline
    for (const containerName of containerNames) {
      const containerData = data[containerName];
      const cpuData: (number | null)[] = [];
      const memData: (number | null)[] = [];

      let dataIndex = 0;

      for (let i = 0; i < commonTimeline.length; i++) {
        const timestamp = commonTimeline[i];

        // Check if container has data at this exact timestamp
        if (dataIndex < containerData.timestamps.length &&
          Math.abs(containerData.timestamps[dataIndex] - timestamp) < step / 2) {
          // Data exists at this timestamp
          cpuData.push(containerData.cpu[dataIndex]);
          memData.push(containerData.memory[dataIndex]);
          dataIndex++;
        } else {
          // Container hasn't started yet or missing data point
          cpuData.push(null);
          memData.push(null);
        }
      }

      this.cpuHistory.set(containerName, cpuData);
      this.memoryHistory.set(containerName, memData);

      // Update containers list if not already present
      if (!this.containers.find(c => c.name === containerName)) {
        this.containers.push({
          id: containerData.id,
          name: containerName,
          status: 'active', // Assuming historical data implies active
          cpu_usage: containerData.cpu?.[containerData.cpu.length - 1] || 0,
          memory_usage: containerData.memory?.[containerData.memory.length - 1] || 0
        });
      }
    }

    this.updateCharts();
  }

  updateCharts(): void {
    // Preserve current legend selection state
    let cpuSelected: { [key: string]: boolean } = {};
    let memSelected: { [key: string]: boolean } = {};

    // Capture current selection from chart instances
    if (this.cpuChartInstance) {
      try {
        const cpuOption = this.cpuChartInstance.getOption();
        if (cpuOption && cpuOption.legend && cpuOption.legend[0] && cpuOption.legend[0].selected) {
          cpuSelected = { ...cpuOption.legend[0].selected };
        }
      } catch (e) {
        // Ignore errors during option retrieval
      }
    }

    if (this.memoryChartInstance) {
      try {
        const memOption = this.memoryChartInstance.getOption();
        if (memOption && memOption.legend && memOption.legend[0] && memOption.legend[0].selected) {
          memSelected = { ...memOption.legend[0].selected };
        }
      } catch (e) {
        // Ignore errors during option retrieval
      }
    }

    // CPU Chart
    const cpuSeries = this.containers.map(container => ({
      name: container.name,
      type: 'line',
      data: this.cpuHistory.get(container.name) || [],
      smooth: true,
      symbol: 'circle',
      symbolSize: 6
    }));

    this.cpuChartOption = {
      backgroundColor: 'transparent',
      title: {
        text: 'CPU Usage (Cores)',
        left: 'center',
        textStyle: { color: 'black', fontFamily: 'Roboto, sans-serif' }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: this.containers.map(c => c.name),
        bottom: 0,
        textStyle: { color: 'black', fontFamily: 'Roboto, sans-serif' },
        selector: [{ type: 'all', title: 'All' }, { type: 'inverse', title: 'Inv' }],
        selected: Object.keys(cpuSelected).length > 0 ? cpuSelected : undefined
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: this.timeLabels,
        axisLabel: { color: '#000000', fontFamily: 'Roboto, sans-serif', rotate: 30 }
      },
      yAxis: {
        type: 'value',
        name: 'CPU (cores)',
        axisLabel: { color: '#000000', fontFamily: 'Roboto, sans-serif' },
        nameTextStyle: { color: '#000000', fontFamily: 'Roboto, sans-serif' },
        splitLine: { lineStyle: { color: '#e0e0e0' } }
      },
      series: cpuSeries as any[]
    };

    // Memory Chart
    const memorySeries = this.containers.map(container => ({
      name: container.name,
      type: 'line',
      data: this.memoryHistory.get(container.name) || [],
      smooth: true,
      symbol: 'circle',
      symbolSize: 6
    }));

    this.memoryChartOption = {
      backgroundColor: 'transparent',
      title: {
        text: 'Memory Usage (MB)',
        left: 'center',
        textStyle: { color: '#000000', fontFamily: 'Roboto, sans-serif' }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: this.containers.map(c => c.name),
        bottom: 0,
        textStyle: { color: '#000000', fontFamily: 'Roboto, sans-serif' },
        selector: [{ type: 'all', title: 'All' }, { type: 'inverse', title: 'Inv' }],
        selected: Object.keys(memSelected).length > 0 ? memSelected : undefined
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: this.timeLabels,
        axisLabel: { color: '#000000', fontFamily: 'Roboto, sans-serif', rotate: 30 }
      },
      yAxis: {
        type: 'value',
        name: 'Memory (MB)',
        axisLabel: { color: '#000000', fontFamily: 'Roboto, sans-serif' },
        nameTextStyle: { color: '#000000', fontFamily: 'Roboto, sans-serif' },
        splitLine: { lineStyle: { color: '#e0e0e0' } }
      },
      series: memorySeries as any[]
    };
  }

  /**
   * Export CSV with only containers currently visible in charts
   * Reads selection from chart legend state
   */
  exportCSV(): void {
    // Get currently selected (visible) containers from CPU chart legend
    const visibleContainers = this.getVisibleContainers();

    if (visibleContainers.length === 0) {
      alert('No containers are currently visible in the charts. Use the legend to show containers before exporting.');
      return;
    }

    // CSV Header
    const headers = ['Timestamp', 'Container', 'CPU (cores)', 'RAM (MB)'];
    const rows: string[][] = [headers];

    // Collect data for visible containers only
    for (const containerName of visibleContainers) {
      const cpuData = this.cpuHistory.get(containerName);
      const memData = this.memoryHistory.get(containerName);

      if (cpuData && memData) {
        for (let i = 0; i < this.timeLabels.length; i++) {
          const cpu = cpuData[i];
          const mem = memData[i];

          // Skip null values
          if (cpu !== null && mem !== null) {
            rows.push([
              this.timeLabels[i],
              containerName,
              cpu.toString(),
              mem.toString()
            ]);
          }
        }
      }
    }

    // Convert to CSV string
    const csvContent = rows.map(row => row.join(',')).join('\n');

    // Download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    link.setAttribute('download', `metrics_export_${timestamp}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /**
   * Get list of currently visible containers based on chart legend selection
   */
  private getVisibleContainers(): string[] {
    const visible: string[] = [];

    if (this.cpuChartInstance) {
      try {
        const cpuOption = this.cpuChartInstance.getOption();
        if (cpuOption && cpuOption.legend && cpuOption.legend[0]) {
          const selected = cpuOption.legend[0].selected;

          // If no selection state, all are visible
          if (!selected || Object.keys(selected).length === 0) {
            return this.containers.map(c => c.name);
          }

          // Return only containers marked as selected (true)
          for (const [containerName, isSelected] of Object.entries(selected)) {
            if (isSelected) {
              visible.push(containerName);
            }
          }
        }
      } catch (e) {
        // Fallback: export all if can't read selection
        return this.containers.map(c => c.name);
      }
    } else {
      // No chart instance yet, export all
      return this.containers.map(c => c.name);
    }

    return visible;
  }

  // Chart initialization handlers to capture instances
  onCpuChartInit(chartInstance: any): void {
    this.cpuChartInstance = chartInstance;
  }

  onMemoryChartInit(chartInstance: any): void {
    this.memoryChartInstance = chartInstance;
  }
}
