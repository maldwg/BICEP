import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, ViewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
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
}

interface EnsembleBenchmarkSelection {
  selected: boolean;
  ensemble: Ensemble;
}

@Component({
  selector: 'app-start',
  imports: [
    AlertComponent,
    CommonModule,
    FormsModule,
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
  styleUrl: './start.component.scss'
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
  jobs: BenchmarkingJob[] = [];
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
            ruleset_ids: container.ruleset_id ? [container.ruleset_id] : []
          }));
          this.ensembleSelections = data.ensembles.map(ensemble => ({
            selected: false,
            ensemble
          }));
          this.runtimeConfigs = data.runtimeConfigs;
          this.deploymentConfigs = data.deploymentConfigs;
          this.ruleSets = data.ruleSets;
          this.datasets = data.datasets;
          this.loading = false;
        },
        error: err => {
          this.loading = false;
          this.errorPopup.showError(err.error?.error || 'Could not load benchmarking data.', err.status || 500);
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
          this.jobs = response.content;
        },
        error: err => {
          this.errorPopup.showError(err.error?.error || 'Could not load benchmark jobs.', err.status || 500);
        }
      });
  }

  startBenchmarking(): void {
    const targets = this.buildTargetSelections();
    if (targets.length === 0) {
      this.errorPopup.showError('Select at least one IDS or ensemble.', 400);
      return;
    }
    if (this.selectedDatasetIds.length === 0) {
      this.errorPopup.showError('Select at least one dataset.', 400);
      return;
    }

    const payload: BenchmarkJobCreate = {
      targets,
      dataset_ids: this.selectedDatasetIds,
      settle_seconds: Number(this.settleSeconds) || 0,
      repeat_count: Math.max(1, Number(this.repeatCount) || 1)
    };

    this.submitting = true;
    this.benchmarkingService.createBenchmarkingJob(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: response => {
          this.submitting = false;
          this.jobs = [response.content, ...this.jobs.filter(job => job.id !== response.content.id)];
        },
        error: err => {
          this.submitting = false;
          this.errorPopup.showError(err.error?.error || 'Could not start benchmarking.', err.status || 500);
        }
      });
  }

  stopJob(job: BenchmarkingJob): void {
    this.benchmarkingService.stopBenchmarkingJob(job.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: response => {
          this.jobs = this.jobs.map(existing => existing.id === response.content.id ? response.content : existing);
        },
        error: err => {
          this.errorPopup.showError(err.error?.error || 'Could not stop benchmarking.', err.status || 500);
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

  progressValue(job: BenchmarkingJob): number {
    if (!job.total_runs) {
      return 0;
    }
    return Math.round((job.completed_runs / job.total_runs) * 100);
  }

  currentItem(job: BenchmarkingJob): BenchmarkingJobItem | undefined {
    return job.items.find(item => item.status === 'running');
  }

  pendingItems(job: BenchmarkingJob): BenchmarkingJobItem[] {
    return job.items.filter(item => item.status === 'pending');
  }

  completedItems(job: BenchmarkingJob): BenchmarkingJobItem[] {
    return job.items.filter(item => ['completed', 'failed', 'cancelled'].includes(item.status));
  }

  canStop(job: BenchmarkingJob): boolean {
    return ['queued', 'running'].includes(job.status) && !job.stop_requested;
  }

  itemLabel(item: BenchmarkingJobItem): string {
    const config = item.configuration_name ? ` / ${item.configuration_name}` : '';
    const ruleset = item.ruleset_name ? ` / ${item.ruleset_name}` : '';
    const repeat = item.repeat_total > 1 ? ` / run ${item.repeat_index}/${item.repeat_total}` : '';
    return `${item.target_name} / ${item.dataset_name}${config}${ruleset}${repeat}`;
  }

  getConfigurationOptions(selection: ContainerBenchmarkSelection): Configuration[] {
    return selection.container.type === 'CIDS' ? this.deploymentConfigs : this.runtimeConfigs;
  }

  selectedRunCount(): number {
    const selectedDatasets = this.selectedDatasetIds.length;
    if (!selectedDatasets) {
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

  normalizedRepeatCount(): number {
    return Math.max(1, Number(this.repeatCount) || 1);
  }
}
