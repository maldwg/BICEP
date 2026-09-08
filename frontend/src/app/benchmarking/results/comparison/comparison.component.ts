import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { EChartsOption } from 'echarts';
import { NgxEchartsModule } from 'ngx-echarts';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCardModule } from '@angular/material/card';

export interface ComparisonMetric {
  value: string;
  viewValue: string;
  max?: number;
}

export interface ComparisonItem {
  id: number | string;
  label: string;
  metrics: Record<string, number | null | undefined>;
}

@Component({
  selector: 'app-comparison',
  templateUrl: './comparison.component.html',
  styleUrls: ['./comparison.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    NgxEchartsModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatSelectModule,
    FormsModule,
    ReactiveFormsModule,
    MatButtonToggleModule,
    MatCardModule
  ]
})
export class ComparisonComponent implements OnInit, OnChanges {
  @Input() title = 'Comparison Workspace';
  @Input() subtitle = 'Select the criteria that matter for this result type.';
  @Input() items: ComparisonItem[] = [];
  @Input() metrics: ComparisonMetric[] = [];
  @Output() close = new EventEmitter<void>();

  chartOption: EChartsOption = {};
  chartInstance: any;
  selectedMetrics = new FormControl<string[]>([]);
  selectedChartType: 'bar' | 'radar' = 'bar';

  ngOnInit(): void {
    this.setDefaultMetrics();
    this.selectedMetrics.valueChanges.subscribe(() => this.updateChart());
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['metrics']) {
      this.setDefaultMetrics();
    }
    if (changes['items'] || changes['metrics']) {
      this.updateChart();
    }
  }

  onChartInit(instance: any): void {
    this.chartInstance = instance;
  }

  updateChart(): void {
    const selected = (this.selectedMetrics.value || [])
      .filter(metric => this.metrics.some(option => option.value === metric));
    if (!this.items.length || !selected.length) {
      this.chartOption = {};
      return;
    }

    if (this.selectedChartType === 'radar') {
      this.renderRadarChart(selected);
      return;
    }
    this.renderBarChart(selected);
  }

  getMetricLabel(metric: string): string {
    return this.metrics.find(option => option.value === metric)?.viewValue || metric;
  }

  downloadChart(): void {
    if (!this.chartInstance) {
      return;
    }
    const link = document.createElement('a');
    link.download = `benchmark_comparison_${Date.now()}.svg`;
    link.href = this.chartInstance.getDataURL({
      type: 'svg',
      pixelRatio: 2,
      backgroundColor: '#fff'
    });
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  private setDefaultMetrics(): void {
    const allowed = new Set(this.metrics.map(metric => metric.value));
    const current = (this.selectedMetrics.value || []).filter(metric => allowed.has(metric));
    this.selectedMetrics.setValue(
      current.length ? current : this.metrics.slice(0, 3).map(metric => metric.value),
      { emitEvent: false }
    );
  }

  private renderBarChart(metrics: string[]): void {
    this.chartOption = {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: metrics.map(metric => this.getMetricLabel(metric)) },
      grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
      xAxis: {
        type: 'category',
        data: this.items.map(item => item.label),
        axisLabel: { interval: 0, rotate: 28 }
      },
      yAxis: { type: 'value' },
      series: metrics.map(metric => ({
        name: this.getMetricLabel(metric),
        type: 'bar',
        data: this.items.map(item => this.valueFor(item, metric)),
        emphasis: { focus: 'series' }
      })) as any[]
    };
  }

  private renderRadarChart(metrics: string[]): void {
    this.chartOption = {
      tooltip: {},
      legend: { data: this.items.map(item => item.label), bottom: 0 },
      radar: {
        indicator: metrics.map(metric => ({
          name: this.getMetricLabel(metric),
          max: this.maxFor(metric)
        }))
      },
      series: [{
        type: 'radar',
        data: this.items.map(item => ({
          name: item.label,
          value: metrics.map(metric => this.valueFor(item, metric))
        }))
      }]
    };
  }

  private valueFor(item: ComparisonItem, metric: string): number {
    const value = item.metrics[metric];
    return typeof value === 'number' && Number.isFinite(value) ? value : 0;
  }

  private maxFor(metric: string): number {
    const configured = this.metrics.find(option => option.value === metric)?.max;
    if (configured != null) {
      return configured;
    }
    const maximum = Math.max(...this.items.map(item => this.valueFor(item, metric)), 0);
    return maximum > 0 ? Math.ceil(maximum * 1.1) : 1;
  }
}
