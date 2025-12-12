import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxEchartsModule, NGX_ECHARTS_CONFIG } from 'ngx-echarts';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { Subscription, interval, switchMap } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { EChartsOption } from 'echarts';

interface ContainerMetric {
  id: number;
  name: string;
  status: string;
  cpu_usage: number;
  memory_usage: number;
}

@Component({
  selector: 'app-monitoring',
  standalone: true,
  imports: [CommonModule, NgxEchartsModule, MatCardModule, MatIconModule, MatButtonModule, MatSelectModule, MatFormFieldModule, MatInputModule, FormsModule],
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

  // Time range settings
  selectedTimeRange: string = '5m';
  maxDataPoints: number = 60;
  pollingInterValSeconds = 5;

  // Custom time range
  customStartTime: string = '';
  customEndTime: string = '';
  useCustomRange: boolean = false;

  constructor(private http: HttpClient) { }

  ngOnInit(): void {
    // Load historical data first
    this.loadHistoricalData();

    // Poll every 5 seconds for live updates
    this.pollingSubscription = interval(this.pollingInterValSeconds * 1000)
      .pipe(
        switchMap(() => this.http.get<{ content: ContainerMetric[] }>(`${environment.backendUrl}/monitoring/metrics`))
      )
      .subscribe({
        next: (response) => {
          if (!this.useCustomRange) {
            this.updateMetrics(response.content);
          }
        },
        error: (error) => console.error('Error fetching metrics:', error)
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
    // Assuming polling interval of 5 seconds
    switch (this.selectedTimeRange) {
      case '5m':
        this.maxDataPoints = 5 / this.pollingInterValSeconds;
        break;
      case '15m':
        this.maxDataPoints = 15 / this.pollingInterValSeconds;
        break;
      case '30m':
        this.maxDataPoints = 30 / this.pollingInterValSeconds;
        break;
      case '1h':
        this.maxDataPoints = 60 / this.pollingInterValSeconds;
        break;
      case '3h':
        this.maxDataPoints = 180 / this.pollingInterValSeconds;
        break;
    }

    // Load fresh historical data for the new range
    this.loadHistoricalData();
  }

  onCustomTimeChange(): void {
    if (this.customStartTime && this.customEndTime) {
      this.useCustomRange = true;
      this.selectedTimeRange = '';  // Clear quick range selection
      this.loadHistoricalData();
    }
  }

  loadHistoricalData(): void {
    let params: any = { step: '15s' };

    if (this.useCustomRange && this.customStartTime && this.customEndTime) {
      // Convert datetime-local format to ISO
      params.start = new Date(this.customStartTime).toISOString();
      params.end = new Date(this.customEndTime).toISOString();
    } else {
      // Use quick range
      params.start = this.selectedTimeRange || '15m';
      // Don't send 'end' parameter for quick ranges - backend defaults to 'now'
    }

    this.http.get<any>(`${environment.backendUrl}/monitoring/metrics/historical`, { params }).subscribe({
      next: (response) => {
        if (response && response.content) {
          this.loadHistoricalDataToCharts(response.content);
        }
      },
      error: (error) => {
        console.error('Error loading historical data:', error);
        // If no historical data, keep live monitoring
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
      title: {
        text: 'CPU Usage (Cores)',
        left: 'center',
        textStyle: { color: '#e0e0e0' }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: this.containers.map(c => c.name),
        bottom: 0,
        textStyle: { color: '#ccc' }
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
        axisLabel: { color: '#ccc', rotate: 30 }
      },
      yAxis: {
        type: 'value',
        name: 'CPU Cores',
        axisLabel: { color: '#ccc' },
        nameTextStyle: { color: '#ccc' },
        splitLine: { lineStyle: { color: '#333' } }
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
      title: {
        text: 'Memory Usage (MB)',
        left: 'center',
        textStyle: { color: '#e0e0e0' }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: {
        data: this.containers.map(c => c.name),
        bottom: 0,
        textStyle: { color: '#ccc' }
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
        axisLabel: { color: '#ccc', rotate: 30 }
      },
      yAxis: {
        type: 'value',
        name: 'Memory (MB)',
        axisLabel: { color: '#ccc' },
        nameTextStyle: { color: '#ccc' },
        splitLine: { lineStyle: { color: '#333' } }
      },
      series: memorySeries as any[]
    };
  }
}
