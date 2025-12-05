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
import { FormsModule } from '@angular/forms';
import { EChartsOption } from 'echarts';

interface ContainerMetric {
  id: number;
  name: string;
  status: string;
  cpu_usage: number;
  memory_usage: number;
}

interface MetricHistory {
  time: string;
  value: number;
}

@Component({
  selector: 'app-monitoring',
  standalone: true,
  imports: [CommonModule, NgxEchartsModule, MatCardModule, MatIconModule, MatButtonModule, MatSelectModule, MatFormFieldModule, FormsModule],
  templateUrl: './monitoring.component.html',
  styleUrl: './monitoring.component.css',
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
  cpuHistory: Map<string, number[]> = new Map();
  memoryHistory: Map<string, number[]> = new Map();
  timeLabels: string[] = [];

  // Chart options
  cpuChartOption: EChartsOption = {};
  memoryChartOption: EChartsOption = {};

  // Time range settings
  selectedTimeRange: string = '15m';
  maxDataPoints: number = 60; // Default for 15 minutes (15 * 60 / 15s = 60 points)

  constructor(private http: HttpClient) { }

  ngOnInit(): void {
    // Poll every 5 seconds
    this.pollingSubscription = interval(5000)
      .pipe(
        switchMap(() => this.http.get<{ content: ContainerMetric[] }>(`${environment.backendUrl}/monitoring/metrics`))
      )
      .subscribe({
        next: (response) => {
          this.updateMetrics(response.content);
        },
        error: (error) => console.error('Error fetching metrics:', error)
      });

    // Initial fetch
    this.http.get<{ content: ContainerMetric[] }>(`${environment.backendUrl}/monitoring/metrics`)
      .subscribe({
        next: (response) => {
          this.updateMetrics(response.content);
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

  onTimeRangeChange(): void {
    // Update maxDataPoints based on selected time range
    // Assuming polling interval of 5 seconds
    switch (this.selectedTimeRange) {
      case '5m':
        this.maxDataPoints = 60; // 5 min * 60 sec / 5 sec
        break;
      case '15m':
        this.maxDataPoints = 180; // 15 min * 60 sec / 5 sec
        break;
      case '30m':
        this.maxDataPoints = 360;
        break;
      case '1h':
        this.maxDataPoints = 720;
        break;
      case '3h':
        this.maxDataPoints = 2160;
        break;
    }

    // Trim existing data to new maxDataPoints
    this.timeLabels = this.timeLabels.slice(-this.maxDataPoints);
    this.cpuHistory.forEach((history, key) => {
      this.cpuHistory.set(key, history.slice(-this.maxDataPoints));
    });
    this.memoryHistory.forEach((history, key) => {
      this.memoryHistory.set(key, history.slice(-this.maxDataPoints));
    });

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
