import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit, ViewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { IdsService } from '../services/ids/ids.service';
import { Container } from '../models/container';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { EnsembleService } from '../services/ensemble/ensemble.service';
import { Ensemble, EnsembleContainer, EnsembleTechnique, EnsembleUpdateData } from '../models/ensemble';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDialog } from '@angular/material/dialog';
import { IdsEditComponent } from './ids-edit/ids-edit.component';
import { EnsembleEditComponent } from './ensemble-edit/ensemble-edit.component';
import { ConfigService } from '../services/config/config.service';
import { IdsTool } from '../models/ids';
import { Configuration } from '../models/configuration';
import { fileTypes } from '../models/acceptedFileTypes';
import { StartAnalysisComponent } from './start-analysis/start-analysis.component';
import { NetworkAnalysisData, StaticAnalysisData, stop_analysisData, analysisTypes } from '../models/analysis';
import { statusTypes } from '../models/status';
import { DatasetService } from '../services/dataset/dataset.service';
import { Dataset } from '../models/dataset';
import { MatIconModule } from '@angular/material/icon';
import { DockerHostService } from '../services/host/host.service';
import { DockerHostSystem } from '../models/host';
import { AlertComponent } from "../components/alert-component/alert-component.component";
import { interval, startWith, switchMap } from 'rxjs';

@Component({
  selector: 'app-dashboard',
  imports: [MatCardModule, CommonModule, MatButtonModule, MatExpansionModule, MatIconModule, AlertComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardComponent implements OnInit {
  @ViewChild(AlertComponent) errorPopup!: AlertComponent;
  containerList: Container[] = [];
  ensembleList: Ensemble[] = [];
  idsToolList: IdsTool[] = [];
  configList: Configuration[] = [];
  datasetList: Dataset[] = [];
  ensembleTechniqueList: EnsembleTechnique[] = [];
  ensembleContainerList: EnsembleContainer[] = [];
  dockerHostList: DockerHostSystem[] = [];
  configNameById = new Map<number, string>();
  idsToolNameById = new Map<number, string>();
  ensembleTechniqueNameById = new Map<number, string>();
  hostNameById = new Map<number, string>();
  ensembleContainerNamesById = new Map<number, string>();
  ensembleContainersIdleById = new Map<number, boolean>();

  constructor(
    private idsService: IdsService,
    public idsDialog: MatDialog,
    public EnsembleDialog: MatDialog,
    public AnalysisDialog: MatDialog,
    private ensembleService: EnsembleService,
    private configService: ConfigService,
    private datasetService: DatasetService,
    private hostService: DockerHostService,
    private destroyRef: DestroyRef,
    private cdr: ChangeDetectorRef

  ) { }

  // TODO 5: do not allow analyssis if other container of ensemble is running, so if ensemble is not idle do not allow for executions!

  readonly pollDelayMs = 10000;

  ngOnInit(): void {
    this.getAllContainer();
    this.getAllEnsembles();
    this.getAllConfigs();
    this.getAllDatasets();
    this.getAllIdsTools();
    this.getAllTechnqiues();
    this.getAllEnsembleContainer();
    this.getAllHosts();
  }

  getAllContainer(): void {
    interval(this.pollDelayMs)
      .pipe(
        startWith(0),
        switchMap(() => this.idsService.getAllIdsContainer()),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(data => {
        this.containerList = data;
        this.rebuildDashboardLookups();
      });
  }

  getAllConfigs() {
    this.configService.getAllConfigurations()
      .subscribe(data => {
        this.configList = data;
        this.configNameById = this.toNameMap(data);
        this.cdr.markForCheck();
      });
  }

  getAllDatasets() {
    this.datasetService.getAllDatasets()
      .subscribe(data => {
        this.datasetList = data
        this.cdr.markForCheck();
      });
  }

  getAllTechnqiues() {
    this.ensembleService.getAllTechnqiues()
      .subscribe(data => {
        this.ensembleTechniqueList = data;
        this.ensembleTechniqueNameById = this.toNameMap(data);
        this.cdr.markForCheck();
      });
  }

  getAllIdsTools() {
    this.idsService.getAllIdsTools()
      .subscribe(data => {
        this.idsToolList = data;
        this.idsToolNameById = this.toNameMap(data);
        this.cdr.markForCheck();
      });
  }

  getAllEnsembles() {
    interval(this.pollDelayMs)
      .pipe(
        startWith(0),
        switchMap(() => this.ensembleService.getAllEnsembles()),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(data => {
        this.ensembleList = data;
        this.rebuildDashboardLookups();
      });
  }

  getAllEnsembleContainer() {
    interval(this.pollDelayMs)
      .pipe(
        startWith(0),
        switchMap(() => this.ensembleService.getEnsembleContainers()),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(data => {
        this.ensembleContainerList = data;
        this.rebuildDashboardLookups();
      });
  }

  // TODO 10: if not status code 200 then popup with error code 
  startAnalysis(container: Container) {
    const dialogRef = this.AnalysisDialog.open(StartAnalysisComponent, {
      height: "35%",
      width: "80%",
      data: {
        datasets: this.datasetList
      }
    })
    dialogRef.afterClosed().subscribe(res => {
      console.log(res)
      if (res != null) {
        if (res.type === analysisTypes.static) {
          let staticAnalysisData: StaticAnalysisData = {
            container_id: container.id,
            dataset_id: res.dataset
          }
          this.idsService.start_static_analysis(staticAnalysisData)
            .subscribe(backendRes => {
              container.status = statusTypes.active
              this.rebuildDashboardLookups();
            },
              err => {
                this.errorPopup.showError(err.error["error"], err.status);
              })
        }
        else if (res.type === analysisTypes.network) {
          let networkAnalysisData: NetworkAnalysisData = {
            container_id: container.id
          }

          // TODO 10: Refactor all endpoints like this to propagate backend errors/m,essages
          this.idsService.start_network_analysis(networkAnalysisData)
            .subscribe(backendRes => {
              container.status = statusTypes.active
              this.rebuildDashboardLookups();
            },
              err => {
                this.errorPopup.showError(err.error["error"], err.status);
              })
        }
      }
      else {
        console.log("User Canceled analysis start");
      }
    })
  }

  getAllHosts() {
    this.hostService.getAllHosts()
      .subscribe(hosts => {
        this.dockerHostList = hosts.map(host => ({
          id: host.id,
          name: host.name,
          host: host.host,
          docker_port: host.docker_port
        }));
        this.hostNameById = this.toNameMap(this.dockerHostList);
        this.cdr.markForCheck();
      });
  }


  stop_analysis(container: Container) {
    let stopData: stop_analysisData = {
      container_id: container.id
    }
    console.log("analysis is stopped")
    this.idsService.stop_analysis(stopData)
      .subscribe(
        res => {
          container.status = statusTypes.idle
          this.rebuildDashboardLookups();
        },
        err => {
          this.errorPopup.showError(err.error["error"], err.status);
        })
  }


  startEnsembleAnalysis(ensemble: Ensemble) {
    const dialogRef = this.AnalysisDialog.open(StartAnalysisComponent, {
      height: "35%",
      width: "80%",
      data: {
        datasets: this.datasetList
      }
    });
    dialogRef.afterClosed().subscribe(res => {
      if (res != null) {
        if (res.type === analysisTypes.static) {
          let staticAnalysisData: StaticAnalysisData = {
            ensemble_id: ensemble.id,
            dataset_id: res.dataset
          }
          this.ensembleService.start_static_analysis(staticAnalysisData)
            .subscribe(
              response => {
                ensemble.status = statusTypes.active
                this.rebuildDashboardLookups();
              },
              err => {
                this.errorPopup.showError(err.error["error"], err.status);
              })
        }
        else if (res.type === analysisTypes.network) {
          let networkAnalysisData: NetworkAnalysisData = {
            ensemble_id: ensemble.id
          }
          this.ensembleService.start_network_analysis(networkAnalysisData)
            .subscribe(response => {
              ensemble.status = statusTypes.active
              // TODO 5: update status of each container
              this.rebuildDashboardLookups();
            },
              err => {
                this.errorPopup.showError(err.error["error"], err.status);
              })
        }
      }
      else {
        console.log("Canceled analysis start");
      }
    })
  }

  stopEnsembleAnalysis(ensemble: Ensemble) {
    let stopData: stop_analysisData = {
      ensemble_id: ensemble.id
    }
    this.ensembleService.stop_analysis(stopData)
      .subscribe(res => {
        ensemble.status = statusTypes.idle
        // TODO 5: update containers to dile again 
        this.rebuildDashboardLookups();
      },
        err => {
          this.errorPopup.showError(err.error["error"], err.status);
        })
  }
  editEnsemble(ensemble: Ensemble) {
    const dialogRef = this.EnsembleDialog.open(EnsembleEditComponent, {
      height: "50%",
      width: "50%",
      data: {
        ensemble: ensemble,
        containerList: this.containerList,
        ensembleTechniqueList: this.ensembleTechniqueList,
        ensembleContainerList: this.ensembleContainerList
      },
      backdropClass: "bDrop"

    });
    dialogRef.afterClosed().subscribe(res => {
      // Ensure there is a reason to update
      let previousContainerOfEnsemble = this.ensembleContainerList.filter(e_ids => e_ids.ensemble_id == ensemble.id).map(e_ids => e_ids.ids_system_id.toString())
      if (res != null) {
        let ensembleUpdate: EnsembleUpdateData = {
          id: ensemble.id,
          name: res.name,
          description: res.description,
          technique_id: res.ensembleTechnique,
          container_ids: res.idsContainer
        }
        this.ensembleService.updateEnsemble(ensembleUpdate)
          .subscribe(backendres => {
            ensemble.status = statusTypes.idle
            ensemble.name = ensembleUpdate.name;
            ensemble.description = ensembleUpdate.description;
            ensemble.technique_id = ensembleUpdate.technique_id;
            // TODO 5: update containers to dile again 
            this.rebuildDashboardLookups();
          },
            err => {
              this.errorPopup.showError(err.error["error"], err.status);
            })


        // location.reload();
      }
    })
  }

  edit(container: Container) {
    const dialogRef = this.idsDialog.open(IdsEditComponent, {
      height: "70%",
      width: "60%",
      data: {
        container: container,
        configList: this.configList,
        idsToolList: this.idsToolList
      },
      backdropClass: "bDrop",
    });

    dialogRef.afterClosed().subscribe(res => {
      if (res != null) {
        // res is the updateData object from IdsEditComponent
        this.idsService.updateContainer(res)
          .subscribe(backendres => {
            // Update local state
              container.description = res.description;
              container.configuration_id = res.configuration_id;
              container.ruleset_id = res.ruleset_id;
              if (res.components) {
                container.components = res.components;
              }
              this.rebuildDashboardLookups();
            },
            err => {
              this.errorPopup.showError(err.error["error"], err.status);
            })
      }
    })
  }

  removeEnsemble(ensembleToRemove: Ensemble) {
    this.ensembleService.removeEnsemble(ensembleToRemove)
      .subscribe(backendres => {
        this.ensembleList = this.ensembleList.filter(ensemble => ensemble.id !== ensembleToRemove.id)
        this.rebuildDashboardLookups();
      },
        err => {
          this.errorPopup.showError(err.error["error"], err.status);
        })

  }

  remove(containerToRemove: Container) {
    if (this.containerIsSettingUp(containerToRemove)) {
      this.errorPopup.showError(
        'An IDS that is still setting up cannot be deleted yet.',
        409
      );
      return;
    }

    this.idsService.removeContainerById(containerToRemove.id)
      .subscribe(backendres => {
        this.containerList = this.containerList.filter(container => container !== containerToRemove);
        this.rebuildDashboardLookups();
      },
        err => {
          this.errorPopup.showError(err.error["error"], err.status);
        })

  }

  private toNameMap<T extends { id: number; name: string }>(items: T[]): Map<number, string> {
    return new Map(items.map(item => [item.id, item.name]));
  }

  private rebuildDashboardLookups(): void {
    const containersById = new Map(this.containerList.map(container => [container.id, container]));
    const namesByEnsemble = new Map<number, string>();
    const idleByEnsemble = new Map<number, boolean>();

    for (const ensemble of this.ensembleList) {
      const ensembleContainers = this.ensembleContainerList
        .filter(link => link.ensemble_id === ensemble.id)
        .map(link => containersById.get(link.ids_system_id))
        .filter((container): container is Container => Boolean(container));

      namesByEnsemble.set(ensemble.id, ensembleContainers.map(container => container.name).join(', '));
      idleByEnsemble.set(
        ensemble.id,
        ensemble.status !== statusTypes.idle || ensembleContainers.every(container => container.status === statusTypes.idle)
      );
    }

    this.ensembleContainerNamesById = namesByEnsemble;
    this.ensembleContainersIdleById = idleByEnsemble;
    this.cdr.markForCheck();
  }


  getConfigName(configId: number) {
    return this.configList.find(c => c.id == configId)?.name;
  }

  getDatasetName(datasetId: number) {
    return this.datasetList.find(d => d.id == datasetId)?.name;
  }

  getIdsToolName(toolId: number) {
    return this.idsToolList.find(t => t.id == toolId)?.name;
  }

  getEnsembleTechniqueName(techniqueId: number) {
    return this.ensembleTechniqueList.find(t => t.id == techniqueId)?.name;
  }

  containerIsIdle(container: Container) {
    if (container.status !== statusTypes.idle) {
      return false;
    }
    else {
      return true;
    }
  }


  containerIsActive(container: Container) {
    if (container.status !== statusTypes.active) {
      return false;
    }
    else {
      return true;
    }
  }


  containerIsSettingUp(container: Container) {
    if (container.status !== statusTypes.setting_up) {
      return false;
    }
    else {
      return true;
    }
  }

  containerCanBeDeleted(container: Container) {
    return !this.containerIsSettingUp(container);
  }

  ensembleIsIdle(ensemble: Ensemble) {
    if (ensemble.status !== statusTypes.idle) {
      return false;
    }
    else {
      return true;
    }
  }

  getEnsembleContainerFromEnsembleId(id: number) {
    return this.ensembleContainerList.filter(e => e.ensemble_id == id);
  }

  getEnsembleContainerNamesFromEnsembleId(id: number) {
    let ensembleContainer: EnsembleContainer[] = this.getEnsembleContainerFromEnsembleId(id);
    let containerIds = ensembleContainer.map(e => e.ids_system_id);
    return this.containerList.filter(c => containerIds.includes(c.id)).map(c => c.name);
  }

  checkEnsembleContainersAreIdleByEnsembleId(ensemble: Ensemble) {
    if (ensemble.status !== statusTypes.idle) {
      return true
    }
    let ensembleContainerIds: number[] = this.getEnsembleContainerFromEnsembleId(ensemble.id).map(c => c.ids_system_id);
    let containers: Container[] = this.containerList.filter(c => ensembleContainerIds.includes(c.id));
    let flag: boolean = true
    containers.forEach(container => {
      if (container.status !== statusTypes.idle) {
        flag = false;
      }
    });
    return flag;
  }

  getHostName(id: number) {
    return this.dockerHostList.find(host => host.id == id)?.name;
  }

  arrayEquals(a: Array<any>, b: Array<any>) {
    return Array.isArray(a) &&
      Array.isArray(b) &&
      a.length === b.length &&
      a.every((val, index) => val === b[index]);
  }

}
