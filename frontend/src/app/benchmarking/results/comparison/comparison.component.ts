import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { BenchmarkingResultsItem } from '../../../models/benchmarking';
import { EChartsOption } from 'echarts';
import { NgxEchartsModule } from 'ngx-echarts';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonToggleModule } from '@angular/material/button-toggle';

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
        MatRadioModule,
        FormsModule,
        ReactiveFormsModule,
        MatCheckboxModule,
        MatButtonToggleModule
    ]
})
export class ComparisonComponent implements OnInit, OnChanges {
    @Input() items: BenchmarkingResultsItem[] = [];
    @Output() close = new EventEmitter<void>();

    chartOption: EChartsOption = {};
    chartInstance: any;

    metrics = [
        { value: 'detection_rate', viewValue: 'Detection Rate' },
        { value: 'fpr', viewValue: 'FPR' },
        { value: 'fnr', viewValue: 'FNR' },
        { value: 'fdr', viewValue: 'FDR' },
        { value: 'acc', viewValue: 'Accuracy' },
        { value: 'prec', viewValue: 'Precision' },
        { value: 'f1_score', viewValue: 'F1 Score' },
        { value: 'runtime', viewValue: 'Runtime' }
    ];

    selectedMetrics = new FormControl(['detection_rate', 'acc', 'f1_score']);
    selectedChartType = 'bar';
    aggregationMethod = 'none'; // 'none', 'average', 'median'

    ngOnInit(): void {
        this.updateChart();
        this.selectedMetrics.valueChanges.subscribe(() => this.updateChart());
    }

    ngOnChanges(changes: SimpleChanges): void {
        if (changes['items']) {
            this.updateChart();
        }
    }

    onChartInit(ec: any) {
        this.chartInstance = ec;
    }

    updateChart() {
        if (!this.items || this.items.length === 0) return;

        const metrics = this.selectedMetrics.value || [];
        const dataToRender = this.getProcessedData();

        if (this.selectedChartType === 'bar') {
            this.renderBarChart(dataToRender, metrics);
        } else if (this.selectedChartType === 'radar') {
            this.renderRadarChart(dataToRender, metrics);
        } else if (this.selectedChartType === 'boxplot') {
            this.renderBoxplot(dataToRender, metrics);
        }
    }

    getProcessedData(): any[] {
        if (this.aggregationMethod === 'none') {
            return this.items.map(item => ({
                ...item,
                displayName: `${item.ids_name} (ID: ${item.id})`
            }));
        }

        // Group by IDS Name
        const grouped = this.items.reduce((acc, item) => {
            if (!acc[item.ids_name]) {
                acc[item.ids_name] = [];
            }
            acc[item.ids_name].push(item);
            return acc;
        }, {} as { [key: string]: BenchmarkingResultsItem[] });

        // Aggregate
        return Object.keys(grouped).map(idsName => {
            const group = grouped[idsName];
            const aggregatedItem: any = { ids_name: idsName, displayName: idsName };

            this.metrics.forEach(m => {
                const values = group.map(item => Number(item[m.value as keyof BenchmarkingResultsItem]));
                if (this.aggregationMethod === 'average') {
                    aggregatedItem[m.value] = values.reduce((a, b) => a + b, 0) / values.length;
                } else if (this.aggregationMethod === 'median') {
                    values.sort((a, b) => a - b);
                    const mid = Math.floor(values.length / 2);
                    aggregatedItem[m.value] = values.length % 2 !== 0 ? values[mid] : (values[mid - 1] + values[mid]) / 2;
                }
            });
            return aggregatedItem;
        });
    }

    renderBarChart(items: any[], metrics: string[]) {
        const series = metrics.map(metric => {
            return {
                name: this.getMetricLabel(metric),
                type: 'bar',
                data: items.map(item => item[metric]),
                label: {
                    show: true,
                    position: 'top',
                    formatter: (params: any) => params.value.toFixed(2)
                }
            };
        });

        this.chartOption = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            legend: {
                data: metrics.map(m => this.getMetricLabel(m))
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: items.map(item => item.displayName),
                axisLabel: { interval: 0, rotate: 30 }
            },
            yAxis: {
                type: 'value'
            },
            series: series as any[]
        };
    }

    renderRadarChart(items: any[], metrics: string[]) {
        const indicator = metrics.map(metric => ({
            name: this.getMetricLabel(metric),
            max: this.getMaxValue(metric)
        }));

        const data = items.map(item => ({
            value: metrics.map(metric => item[metric]),
            name: item.displayName
        }));

        this.chartOption = {
            tooltip: {},
            legend: {
                data: items.map(item => item.displayName),
                bottom: 0
            },
            radar: {
                indicator: indicator
            },
            series: [{
                name: 'Comparison',
                type: 'radar',
                data: data as any[]
            }]
        };
    }

    renderBoxplot(items: any[], metrics: string[]) {
        // For boxplot, we ideally want to show the distribution of the *original* data points for each IDS/Metric
        // If aggregation is ON, boxplot doesn't make much sense for the aggregated value itself (it's a single point).
        // So, if aggregation is ON, we might want to disable boxplot or show the distribution of the group.

        // Let's implement:
        // If Aggregation is NONE: Show distribution of metrics across the selected individual runs (same as before).
        // If Aggregation is AVG/MEDIAN: It's better to show the distribution of the *groups* (IDS Names).

        let sourceData: any[] = [];
        let axisData: string[] = [];

        if (this.aggregationMethod === 'none') {
            // Treat metrics as categories
            sourceData = metrics.map(metric => items.map(item => Number(item[metric])));
            axisData = metrics.map(m => this.getMetricLabel(m));
        } else {
            // Group by IDS Name is already done in getProcessedData, but for boxplot we need the raw values
            // So we need to re-group here if we want to show boxplots per IDS.
            // Actually, the user requirement "provide an option to group results by IDS name... and then only display the median or average"
            // implies that for Bar/Radar we show the single value. For Boxplot, showing the distribution IS the point.

            // Let's stick to the previous implementation for now where we show metric distribution across the *displayed* items.
            sourceData = metrics.map(metric => items.map(item => Number(item[metric])));
            axisData = metrics.map(m => this.getMetricLabel(m));
        }

        this.chartOption = {
            title: [
                {
                    text: 'Metric Distribution',
                    left: 'center',
                }
            ],
            dataset: [
                {
                    source: sourceData
                },
                {
                    transform: {
                        type: 'boxplot',
                        config: { itemNameFormatter: (params: any) => axisData[params.value] }
                    }
                },
                {
                    fromDatasetIndex: 1,
                    fromTransformResult: 1
                }
            ],
            tooltip: {
                trigger: 'item',
                axisPointer: {
                    type: 'shadow'
                }
            },
            grid: {
                left: '10%',
                right: '10%',
                bottom: '15%'
            },
            xAxis: {
                type: 'category',
                boundaryGap: true,
                nameGap: 30,
                splitArea: {
                    show: false
                },
                splitLine: {
                    show: false
                }
            },
            yAxis: {
                type: 'value',
                splitArea: {
                    show: true
                }
            },
            series: [
                {
                    name: 'boxplot',
                    type: 'boxplot',
                    datasetIndex: 1
                },
                {
                    name: 'outlier',
                    type: 'scatter',
                    datasetIndex: 2
                }
            ]
        };
    }

    getMetricLabel(metric: string): string {
        return this.metrics.find(m => m.value === metric)?.viewValue || metric;
    }

    getMaxValue(metric: string): number {
        if (['detection_rate', 'acc', 'prec', 'f1_score'].includes(metric)) return 1.0;
        if (['fpr', 'fnr', 'fdr'].includes(metric)) return 1.0;
        return 100;
    }

    downloadChart() {
        if (this.chartInstance) {
            const url = this.chartInstance.getDataURL({
                type: 'svg',
                pixelRatio: 2,
                backgroundColor: '#fff'
            });
            const link = document.createElement('a');
            link.download = `chart_${new Date().getTime()}.svg`;
            link.href = url;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
}
