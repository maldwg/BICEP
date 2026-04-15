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
import { MatCardModule } from '@angular/material/card';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

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
        MatButtonToggleModule,
        MatCardModule
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
        { value: 'runtime', viewValue: 'Runtime' },
        { value: 'cpu_usage', viewValue: 'CPU Usage (cores)' },
        { value: 'memory_usage', viewValue: 'RAM Usage (MB)' }
    ];

    selectedMetrics = new FormControl(['detection_rate', 'acc', 'f1_score']);
    selectedChartType = 'bar';
    aggregationMethod = 'none'; // 'none', 'average', 'median'

    // Cache for series data
    seriesDataCache: { [key: number]: { cpu: number[], memory: number[] } } = {};

    constructor(private http: HttpClient) { }

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

    async updateChart() {
        if (!this.items || this.items.length === 0) return;

        const metrics = this.selectedMetrics.value || [];

        // Check if resource metrics are selected
        const hasResourceMetrics = metrics.some(m => m === 'cpu_usage' || m === 'memory_usage');

        if (hasResourceMetrics) {
            await this.fetchSeriesDataIfNeeded();
        }

        const dataToRender = this.getProcessedData();

        if (this.selectedChartType === 'bar') {
            this.renderBarChart(dataToRender, metrics);
        } else if (this.selectedChartType === 'radar') {
            this.renderRadarChart(dataToRender, metrics);
        } else if (this.selectedChartType === 'boxplot') {
            this.renderBoxplot(dataToRender, metrics);
        }
    }

    async fetchSeriesDataIfNeeded() {
        const itemsToFetch = this.items.filter(item => !this.seriesDataCache[item.id]);

        if (itemsToFetch.length === 0) return;

        const requests = itemsToFetch.map(item => ({
            id: item.id,
            container_name: item.ids_name, // Assuming ids_name is the container name
            start_time: item.start_time,
            end_time: item.stop_time
        }));

        try {
            const response = await this.http.post<{ content: { [key: number]: { cpu: number[], memory: number[] } } }>(
                `${environment.backendUrl}/benchmarking/metrics/series`,
                requests
            ).toPromise();

            if (response && response.content) {
                this.seriesDataCache = { ...this.seriesDataCache, ...response.content };
            }
        } catch (error) {
            console.error("Failed to fetch series data", error);
        }
    }

    getProcessedData(): any[] {
        if (this.aggregationMethod === 'none') {
            return this.items.map(item => {
                const cached = this.seriesDataCache[item.id];
                return {
                    ...item,
                    displayName: `${item.ids_name} (ID: ${item.id})`,
                    cpu_usage: cached ? cached.cpu : [],
                    memory_usage: cached ? cached.memory : []
                };
            });
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
                if (m.value === 'cpu_usage' || m.value === 'memory_usage') {
                    // For resource metrics, we aggregate all series data
                    const allValues: number[] = [];
                    group.forEach(item => {
                        const cached = this.seriesDataCache[item.id];
                        if (cached) {
                            if (m.value === 'cpu_usage') allValues.push(...cached.cpu);
                            if (m.value === 'memory_usage') allValues.push(...cached.memory);
                        }
                    });
                    aggregatedItem[m.value] = allValues;
                } else {
                    const values = group.map(item => Number(item[m.value as keyof BenchmarkingResultsItem]));
                    if (this.aggregationMethod === 'average') {
                        aggregatedItem[m.value] = values.reduce((a, b) => a + b, 0) / values.length;
                    } else if (this.aggregationMethod === 'median') {
                        values.sort((a, b) => a - b);
                        const mid = Math.floor(values.length / 2);
                        aggregatedItem[m.value] = values.length % 2 !== 0 ? values[mid] : (values[mid - 1] + values[mid]) / 2;
                    }
                }
            });
            return aggregatedItem;
        });
    }

    renderBarChart(items: any[], metrics: string[]) {
        // Filter out resource metrics for bar chart as they are arrays
        const validMetrics = metrics.filter(m => m !== 'cpu_usage' && m !== 'memory_usage');

        const series = validMetrics.map(metric => {
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
                data: validMetrics.map(m => this.getMetricLabel(m))
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
        // Filter out resource metrics
        const validMetrics = metrics.filter(m => m !== 'cpu_usage' && m !== 'memory_usage');

        const indicator = validMetrics.map(metric => ({
            name: this.getMetricLabel(metric),
            max: this.getMaxValue(metric)
        }));

        const data = items.map(item => ({
            value: validMetrics.map(metric => item[metric]),
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
        // Handle resource metrics differently:
        // If resource metrics are selected, we show boxplots of the time-series data for each run/group.
        // If standard metrics are selected, we show distribution across runs (as before).

        // Check if we have resource metrics mixed with standard metrics
        const resourceMetrics = metrics.filter(m => m === 'cpu_usage' || m === 'memory_usage');
        const groupedDistributionMetrics = metrics.filter(m => m === 'runtime');
        const standardMetrics = metrics.filter(m => m !== 'cpu_usage' && m !== 'memory_usage');

        // Priority: If resource metrics are present, visualize them. 
        // Ideally we shouldn't mix them in one chart if the X-axis meaning changes.
        // Let's visualize the first resource metric if present, or fallback to standard behavior.

        if (resourceMetrics.length > 0) {
            // Visualize distribution of the resource metric for each item (Run or Group)
            const metric = resourceMetrics[0]; // Take the first one

            const sourceData = items.map(item => item[metric] || []);
            const axisData = items.map(item => item.displayName);

            this.chartOption = {
                title: [
                    {
                        text: `${this.getMetricLabel(metric)} Distribution`,
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
                    name: metric === 'cpu_usage' ? 'cores' : 'MB',
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

        } else if (groupedDistributionMetrics.length > 0) {
            const metric = groupedDistributionMetrics[0];
            const groupedRuns = this.items.reduce((acc, item) => {
                if (!acc[item.ids_name]) {
                    acc[item.ids_name] = [];
                }

                acc[item.ids_name].push(Number(item.runtime));
                return acc;
            }, {} as { [key: string]: number[] });

            const axisData = Object.keys(groupedRuns);
            const sourceData = axisData.map(idsName => groupedRuns[idsName]);

            this.chartOption = {
                title: [
                    {
                        text: `${this.getMetricLabel(metric)} Distribution`,
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

        } else {
            // Standard behavior for scalar metrics
            let sourceData: any[] = [];
            let axisData: string[] = [];

            const scalarMetrics = standardMetrics.filter(metric => metric !== 'runtime');
            sourceData = scalarMetrics.map(metric => items.map(item => Number(item[metric])));
            axisData = scalarMetrics.map(m => this.getMetricLabel(m));

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
