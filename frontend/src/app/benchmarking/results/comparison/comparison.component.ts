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

export interface ComparisonClassPerformance {
  label: string;
  isBenign: boolean;
  rate: number | null | undefined;
}

export interface ComparisonItem {
  id: number | string;
  label: string;
  metrics: Record<string, number | null | undefined>;
  classPerformance?: ComparisonClassPerformance[];
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
  classChartOption: EChartsOption = {};
  classChartInstance: any;
  selectedMetrics = new FormControl<string[]>([]);
  selectedChartType: 'bar' | 'radar' = 'bar';

  ngOnInit(): void {
    this.setDefaultMetrics();
    this.updateClassChart();
    this.selectedMetrics.valueChanges.subscribe(() => this.updateChart());
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['metrics']) {
      this.setDefaultMetrics();
    }
    if (changes['items'] || changes['metrics']) {
      this.updateChart();
      this.updateClassChart();
    }
  }

  onChartInit(instance: any): void {
    this.chartInstance = instance;
  }

  onClassChartInit(instance: any): void {
    this.classChartInstance = instance;
  }

  get hasClassPerformanceComparison(): boolean {
    return this.items.filter(item => item.classPerformance?.length).length >= 2;
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

  downloadClassChart(): void {
    if (!this.classChartInstance) {
      return;
    }
    const link = document.createElement('a');
    link.download = 'class_performance_comparison_' + Date.now() + '.svg';
    link.href = this.classChartInstance.getDataURL({
      type: 'svg',
      pixelRatio: 2,
      backgroundColor: '#fff'
    });
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  private updateClassChart(): void {
    if (!this.hasClassPerformanceComparison) {
      this.classChartOption = {};
      return;
    }

    const classes = this.classDescriptors();
    const labels = classes.map(item =>
      item.isBenign ? item.label + '\n(benign FPR)' : item.label
    );

    this.classChartOption = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        valueFormatter: (value: any) =>
          typeof value === 'number' ? (value * 100).toFixed(2) + '%' : 'N/A'
      },
      legend: { type: 'scroll', top: 0 },
      grid: { left: '3%', right: '4%', top: 72, bottom: classes.length > 8 ? 92 : 54, containLabel: true },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { interval: 0, rotate: classes.length > 5 ? 24 : 0 }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 1,
        name: 'Rate',
        axisLabel: { formatter: (value: number) => Math.round(value * 100) + '%' }
      },
      dataZoom: classes.length > 8
        ? [
            { type: 'inside', xAxisIndex: 0 },
            { type: 'slider', xAxisIndex: 0, start: 0, end: Math.min(100, 800 / classes.length) }
          ]
        : [],
      series: this.items
        .filter(item => item.classPerformance?.length)
        .map(item => ({
          name: item.label,
          type: 'bar',
          data: classes.map(classItem =>
            item.classPerformance?.find(value => value.label === classItem.label)?.rate ?? null
          ),
          emphasis: { focus: 'series' }
        })) as any[]
    };
  }

  private classDescriptors(): ComparisonClassPerformance[] {
    const classes = new Map<string, ComparisonClassPerformance>();
    this.items.forEach(item =>
      item.classPerformance?.forEach(classItem => {
        if (!classes.has(classItem.label)) {
          classes.set(classItem.label, classItem);
        }
      })
    );
    return Array.from(classes.values());
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
