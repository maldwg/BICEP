import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit, ViewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { forkJoin, interval, startWith, switchMap } from 'rxjs';
import { AlertComponent } from '../../components/alert-component/alert-component.component';
import { Configuration } from '../../models/configuration';
import { Container } from '../../models/container';
import { Dataset } from '../../models/dataset';
import { Ensemble } from '../../models/ensemble';
import {
  BenchmarkingJob,
  BenchmarkingJobItem,
  BenchmarkJobCreate,
  BenchmarkTargetSelection
} from '../../models/benchmarking';
import { fileTypes } from '../../models/acceptedFileTypes';
import { BenchmarkingService } from '../../services/benchmarking/benchmarking.service';
import { ConfigService } from '../../services/config/config.service';
import { DatasetService } from '../../services/dataset/dataset.service';
import { EnsembleService } from '../../services/ensemble/ensemble.service';
import { IdsService } from '../../services/ids/ids.service';

interface ContainerBenchmarkSelection {
  selected: boolean;
  container: Container;
  configuration_ids: number[];
  ruleset_ids: number[];
  configurationOptions: Configuration[];
}

interface EnsembleBenchmarkSelection {
  selected: boolean;
  ensemble: Ensemble;
}

interface BenchmarkingJobItemView extends BenchmarkingJobItem {
  label: string;
}

interface BenchmarkingJobView extends BenchmarkingJob {
  progressValue: number;
  currentItem?: BenchmarkingJobItemView;
  canStop: boolean;
  items: BenchmarkingJobItemView[];
}

@Component({
  selector: 'app-start',
  imports: [
    AlertComponent,
    CommonModule,
    FormsModule,
    MatButtonToggleModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDividerModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressBarModule,
    MatSelectModule
  ],
  templateUrl: './start.component.html',
  styleUrl: './start.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class StartComponent implements OnInit {
  @ViewChild(AlertComponent) errorPopup!: AlertComponent;

  containerSelections: ContainerBenchmarkSelection[] = [];
  ensembleSelections: EnsembleBenchmarkSelection[] = [];
  datasets: Dataset[] = [];
  runtimeConfigs: Configuration[] = [];
  deploymentConfigs: Configuration[] = [];
  ruleSets: Configuration[] = [];
  selectedDatasetIds: number[] = [];
  settleSeconds = 5;
  repeatCount = 1;
  benchmarkMode: 'static_dataset' | 'throughput' = 'static_dataset';
  trafficMode: 'packet_generator' | 'iperf' = 'packet_generator';
  packetCount = 1000;
  ratePps = 100;
  payloadSize = 64;
  packetProtocol: 'tcp' | 'udp' | 'icmp' = 'udp';
  sourceIp = '';
  destinationIp = '';
  sourcePort = 40000;
  destinationPort = 50000;
  payload = '';
  iperfDuration = 10;
  iperfParallel = 1;
  iperfProtocol: 'tcp' | 'udp' = 'tcp';
  iperfBandwidth = '';
  analysisWaitSeconds = 5;
  preparedRunCount = 0;
  jobs: BenchmarkingJobView[] = [];
  loading = true;
  submitting = false;

  private readonly jobPollDelayMs = 5000;

  constructor(
    private idsService: IdsService,
    private ensembleService: EnsembleService,
    private configService: ConfigService,
    private datasetService: DatasetService,
    private benchmarkingService: BenchmarkingService,
    private destroyRef: DestroyRef,
    private cdr: ChangeDetectorRef,
  ) { }

  ngOnInit(): void {
    this.loadBenchmarkScope();
    this.pollJobs();
  }

  loadBenchmarkScope(): void {
    forkJoin({
      containers: this.idsService.getAllNonEnsembledIdsContainer(),
      ensembles: this.ensembleService.getAllEnsembles(),
      runtimeConfigs: this.configService.getAllConfigurationsByType(fileTypes.runtime),
      deploymentConfigs: this.configService.getAllConfigurationsByType(fileTypes.deployment),
      ruleSets: this.configService.getAllConfigurationsByType(fileTypes.ruleSet),
      datasets: this.datasetService.getAllDatasets()
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: data => {
          this.containerSelections = data.containers.map(container => ({
            selected: false,
            container,
            configuration_ids: container.configuration_id ? [container.configuration_id] : [],
            ruleset_ids: container.ruleset_id ? [container.ruleset_id] : [],
            configurationOptions: container.type === 'CIDS' ? data.deploymentConfigs : data.runtimeConfigs
          }));
          this.ensembleSelections = data.ensembles.map(ensemble => ({
            selected: false,
            ensemble
          }));
          this.runtimeConfigs = data.runtimeConfigs;
          this.deploymentConfigs = data.deploymentConfigs;
          this.ruleSets = data.ruleSets;
          this.datasets = data.datasets;
          this.refreshSelectedRunCount();
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: err => {
          this.loading = false;
          this.errorPopup.showError(err.error?.error || 'Could not load benchmarking data.', err.status || 500);
          this.cdr.markForCheck();
        }
      });
  }

  pollJobs(): void {
    interval(this.jobPollDelayMs)
      .pipe(
        startWith(0),
        switchMap(() => this.benchmarkingService.getBenchmarkingJobs(25)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: response => {
          this.jobs = response.content.map(job => this.toJobView(job));
          this.cdr.markForCheck();
        },
        error: err => {
          this.errorPopup.showError(err.error?.error || 'Could not load benchmark jobs.', err.status || 500);
          this.cdr.markForCheck();
        }
      });
  }

  startBenchmarking(): void {
    const targets = this.buildTargetSelections();
    if (targets.length === 0) {
      this.errorPopup.showError('Select at least one IDS or ensemble.', 400);
      return;
    }
    if (this.benchmarkMode === 'static_dataset' && this.selectedDatasetIds.length === 0) {
      this.errorPopup.showError('Select at least one dataset.', 400);
      return;
    }

    const payload: BenchmarkJobCreate = {
      targets,
      dataset_ids: this.benchmarkMode === 'static_dataset' ? this.selectedDatasetIds : [],
      settle_seconds: Number(this.settleSeconds) || 0,
      repeat_count: Math.max(1, Number(this.repeatCount) || 1),
      mode: this.benchmarkMode,
      traffic_mode: this.trafficMode,
      packet_count: Math.max(1, Number(this.packetCount) || 1),
      rate_pps: Math.max(0, Number(this.ratePps) || 0),
      payload_size: Math.max(0, Number(this.payloadSize) || 0),
      protocol: this.packetProtocol,
      source_ip: this.sourceIp.trim() || null,
      destination_ip: this.destinationIp.trim() || null,
      source_port: Math.max(1, Number(this.sourcePort) || 1),
      destination_port: Math.max(1, Number(this.destinationPort) || 1),
      payload: this.payload || null,
      iperf_duration: Math.max(1, Number(this.iperfDuration) || 1),
      iperf_parallel: Math.max(1, Number(this.iperfParallel) || 1),
      iperf_protocol: this.iperfProtocol,
      iperf_bandwidth: this.iperfBandwidth.trim() || null,
      analysis_wait_seconds: Math.max(0, Number(this.analysisWaitSeconds) || 0)
    };

    this.submitting = true;
    this.benchmarkingService.createBenchmarkingJob(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: response => {
          this.submitting = false;
          const job = this.toJobView(response.content);
          this.jobs = [job, ...this.jobs.filter(existing => existing.id !== job.id)];
          this.cdr.markForCheck();
        },
        error: err => {
          this.submitting = false;
          this.errorPopup.showError(err.error?.error || 'Could not start benchmarking.', err.status || 500);
          this.cdr.markForCheck();
        }
      });
  }

  stopJob(job: BenchmarkingJobView): void {
    this.benchmarkingService.stopBenchmarkingJob(job.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: response => {
          const job = this.toJobView(response.content);
          this.jobs = this.jobs.map(existing => existing.id === job.id ? job : existing);
          this.cdr.markForCheck();
        },
        error: err => {
          this.errorPopup.showError(err.error?.error || 'Could not stop benchmarking.', err.status || 500);
          this.cdr.markForCheck();
        }
      });
  }

  buildTargetSelections(): BenchmarkTargetSelection[] {
    const containerTargets: BenchmarkTargetSelection[] = this.containerSelections
      .filter(selection => selection.selected)
      .map(selection => ({
        target_type: 'container',
        target_id: selection.container.id,
        configuration_ids: selection.configuration_ids,
        ruleset_ids: selection.ruleset_ids
      }));

    const ensembleTargets: BenchmarkTargetSelection[] = this.ensembleSelections
      .filter(selection => selection.selected)
      .map(selection => ({
        target_type: 'ensemble',
        target_id: selection.ensemble.id,
        configuration_ids: [],
        ruleset_ids: []
      }));

    return [...containerTargets, ...ensembleTargets];
  }

  refreshSelectedRunCount(): void {
    this.preparedRunCount = this.calculateSelectedRunCount();
    this.cdr.markForCheck();
  }

  setBenchmarkMode(mode: 'static_dataset' | 'throughput'): void {
    this.benchmarkMode = mode;
    this.refreshSelectedRunCount();
  }

  private toJobView(job: BenchmarkingJob): BenchmarkingJobView {
    const items = job.items.map(item => ({
      ...item,
      label: this.itemLabel(item)
    }));

    return {
      ...job,
      items,
      progressValue: this.progressValue(job),
      currentItem: items.find(item => item.status === 'running'),
      canStop: this.canStop(job)
    };
  }

  private progressValue(job: BenchmarkingJob): number {
    if (!job.total_runs) {
      return 0;
    }
    return Math.round((job.completed_runs / job.total_runs) * 100);
  }

  private canStop(job: BenchmarkingJob): boolean {
    return ['queued', 'running'].includes(job.status) && !job.stop_requested;
  }

  private itemLabel(item: BenchmarkingJobItem): string {
    const config = item.configuration_name ? ` / ${item.configuration_name}` : '';
    const ruleset = item.ruleset_name ? ` / ${item.ruleset_name}` : '';
    const repeat = item.repeat_total > 1 ? ` / run ${item.repeat_index}/${item.repeat_total}` : '';
    if (item.dataset_id === 0 || item.traffic_mode) {
      const traffic = item.traffic_mode === 'iperf' ? 'iperf' : 'packets';
      return `${item.target_name} / throughput ${traffic}${config}${ruleset}${repeat}`;
    }
    return `${item.target_name} / ${item.dataset_name}${config}${ruleset}${repeat}`;
  }

  private calculateSelectedRunCount(): number {
    const selectedDatasets = this.benchmarkMode === 'static_dataset' ? this.selectedDatasetIds.length : 1;
    if (!selectedDatasets && this.benchmarkMode === 'static_dataset') {
      return 0;
    }

    const containerRuns = this.containerSelections
      .filter(selection => selection.selected)
      .reduce((total, selection) => {
        const configCount = selection.configuration_ids.length || 1;
        const rulesetCount = selection.ruleset_ids.length || 1;
        return total + (configCount * rulesetCount * selectedDatasets * this.normalizedRepeatCount());
      }, 0);

    const ensembleRuns = this.ensembleSelections.filter(selection => selection.selected).length * selectedDatasets * this.normalizedRepeatCount();
    return containerRuns + ensembleRuns;
  }

  metricLabel(item: BenchmarkingJobItem): string {
    if (!item.throughput_mbps && !item.throughput_pps) {
      return item.status;
    }
    const mbps = item.throughput_mbps !== undefined && item.throughput_mbps !== null
      ? `${item.throughput_mbps.toFixed(2)} Mbps`
      : '';
    const pps = item.throughput_pps !== undefined && item.throughput_pps !== null
      ? `${item.throughput_pps.toFixed(0)} pps`
      : '';
    return [mbps, pps].filter(Boolean).join(' / ') || item.status;
  }

  normalizedRepeatCount(): number {
    return Math.max(1, Number(this.repeatCount) || 1);
  }
}
