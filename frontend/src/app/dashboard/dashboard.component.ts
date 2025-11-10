import { Component, ViewChild, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { HttpClient, HttpResponse } from '@angular/common/http';
import { IdsService } from '../services/ids/ids.service';
import { Container, ContainerUpdateData } from '../models/container';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { EnsembleService } from '../services/ensemble/ensemble.service';
import { Ensemble, EnsembleContainer, EnsembleTechnique, EnsembleUpdateData } from '../models/ensemble';
import {MatExpansionModule} from '@angular/material/expansion';
import {
  MatDialog,
  MAT_DIALOG_DATA,
  MatDialogRef,
  MatDialogTitle,
  MatDialogContent,
  MatDialogActions,
  MatDialogClose,
} from '@angular/material/dialog';
import { IdsEditComponent } from './ids-edit/ids-edit.component';
import { EnsembleEditComponent } from './ensemble-edit/ensemble-edit.component';
import { ConfigService } from '../services/config/config.service';
import { IdsTool } from '../models/ids';
import { Configuration } from '../models/configuration';
import { fileTypes } from '../models/acceptedFileTypes';
import { StartAnalysisComponent } from './start-analysis/start-analysis.component';
import { NetworkAnalysisData, StaticAnalysisData, stop_analysisData, analysisTypes } from '../models/analysis';
import { statusTypes } from '../models/status';
import { STATUS_CODES } from 'node:http';
import { DatasetService } from '../services/dataset/dataset.service';
import { Dataset } from '../models/dataset';
import { MatIconModule } from '@angular/material/icon';
import { DockerHostService } from '../services/host/host.service';
import { DockerHostSystem } from '../models/host';
import { AlertComponent } from "../components/alert-component/alert-component.component";
import { repeat } from 'rxjs';

@Component({
    selector: 'app-dashboard',
    imports: [MatCardModule, CommonModule, MatButtonModule, MatExpansionModule, MatIconModule, AlertComponent],
    templateUrl: './dashboard.component.html',
    styleUrl: './dashboard.component.scss'
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

  constructor (
    private idsService: IdsService,
    public idsDialog: MatDialog,
    public EnsembleDialog: MatDialog,
    public AnalysisDialog: MatDialog,
    private ensembleService: EnsembleService,
    private configService: ConfigService,
    private datasetService: DatasetService,
    private hostService: DockerHostService
    
  ) {}

  // TODO 5: do not allow analyssis if other container of ensemble is running, so if ensemble is not idle do not allow for executions!

  POLL_DELAY = 5000;

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
  
  getAllContainer(): void{
    this.idsService.getAllIdsContainer()
      .pipe(
        repeat({
          delay: this.POLL_DELAY
        })
      )
      .subscribe(data =>  {
        this.containerList = data
      });
  }

  getAllConfigs(){
    this.configService.getAllConfigurations()
      .subscribe(data => {
        this.configList = data
      });
  }

  getAllDatasets(){
    this.datasetService.getAllDatasets()
      .subscribe(data => {
        this.datasetList = data
      });
  }

  getAllTechnqiues(){
    this.ensembleService.getAllTechnqiues()
      .subscribe(data => {
        this.ensembleTechniqueList = data
      });   
  }

  getAllIdsTools(){
    this.idsService.getAllIdsTools()
      .subscribe(data => {
        this.idsToolList = data
      });
  }

  getAllEnsembles(){
    this.ensembleService.getAllEnsembles()
      .pipe(
        repeat({
          delay: this.POLL_DELAY
        })
      )
      .subscribe(data => {
        this.ensembleList = data
      });
  }

  getAllEnsembleContainer(){
    this.ensembleService.getEnsembleContainers()  
      .pipe(
        repeat({
          delay: this.POLL_DELAY
        })
      )
      .subscribe(data => {
        this.ensembleContainerList = data
      });
  }

  // TODO 10: if not status code 200 then popup with error code 
  startAnalysis(container: Container){
    const dialogRef = this.AnalysisDialog.open(StartAnalysisComponent, {
      height: "35%",
      width: "80%",
      data: {
        datasets: this.datasetList
      }
    })
    dialogRef.afterClosed().subscribe(res => {
      console.log(res)
      if(res != null){
        if(res.type === analysisTypes.static){
          let staticAnalysisData: StaticAnalysisData = {
            container_id: container.id,
            dataset_id: res.dataset
          }
          this.idsService.start_static_analysis(staticAnalysisData)
            .subscribe(backendRes => {
                container.status = statusTypes.active
              },
              err => {
                this.errorPopup.showError(err.error["error"], err.status);
            })
        }
        else if(res.type === analysisTypes.network){
          let networkAnalysisData: NetworkAnalysisData = {
            container_id: container.id
          }
  
          // TODO 10: Refactor all endpoints like this to propagate backend errors/m,essages
          this.idsService.start_network_analysis(networkAnalysisData)
            .subscribe(backendRes => {
                container.status = statusTypes.active
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

  getAllHosts(){
    this.hostService.getAllHosts()
      .subscribe(hosts => {
      this.dockerHostList = hosts.map(host => ({
        id: host.id,
        name: host.name,
        host: host.host,
        docker_port: host.docker_port
      }));
    });
  }
  

  stop_analysis(container: Container){
    let stopData: stop_analysisData = {
      container_id: container.id
    }
    console.log("analysis is stopped")
    this.idsService.stop_analysis(stopData)
      .subscribe(
        res => {
          container.status = statusTypes.idle
        },
        err => {
          this.errorPopup.showError(err.error["error"], err.status);
      })
  }


  startEnsembleAnalysis(ensemble: Ensemble){
    const dialogRef = this.AnalysisDialog.open(StartAnalysisComponent, {
      height: "35%",
      width: "80%",
      data: {
        datasets: this.datasetList
      }
    });
    dialogRef.afterClosed().subscribe(res => {
      if(res != null){
        if(res.type === analysisTypes.static){
          let staticAnalysisData: StaticAnalysisData = {
            ensemble_id: ensemble.id,
            dataset_id: res.dataset
          }
          this.ensembleService.start_static_analysis(staticAnalysisData)
            .subscribe( 
              response => {
                ensemble.status = statusTypes.active
              },
              err => {
                this.errorPopup.showError(err.error["error"], err.status);
            })
        }
        else if(res.type === analysisTypes.network){
          let networkAnalysisData: NetworkAnalysisData = {
            ensemble_id: ensemble.id
          }
          this.ensembleService.start_network_analysis(networkAnalysisData)
            .subscribe(response => {
                ensemble.status = statusTypes.active
                // TODO 5: update status of each container
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

  stopEnsembleAnalysis(ensemble: Ensemble){
    let stopData: stop_analysisData = {
      ensemble_id: ensemble.id
    }
    this.ensembleService.stop_analysis(stopData)
      .subscribe(res  => {
          ensemble.status = statusTypes.idle
          // TODO 5: update containers to dile again 
        },
        err => {
          this.errorPopup.showError(err.error["error"], err.status);
      })
  }
  editEnsemble(ensemble: Ensemble){
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
      let previousContainerOfEnsemble = this.ensembleContainerList.filter(e_ids => e_ids.ensemble_id == ensemble.id).map(e_ids => e_ids.ids_container_id.toString())
      if(res != null){
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
            },
            err => {
              this.errorPopup.showError(err.error["error"], err.status);
            })
        
        
        // location.reload();
      } 
    })
  }

  edit(container: Container){
    const dialogRef = this.idsDialog.open(IdsEditComponent, {
      height: "50%",
      width: "50%",
      data: {
        container: container,
        configList: this.configList,
        idsToolList: this.idsToolList
      },
      backdropClass: "bDrop",
    });

    dialogRef.afterClosed().subscribe(res => {
      // Ensure there is at least one field that needs an update
      if(res != null){
        let configId = parseInt(res.config);
        let rulesetId = parseInt(res.ruleset);
        let data: ContainerUpdateData = {
          id: container.id,
          description: res.description,
          configuration_id: configId,
          ruleset_id: rulesetId.toString() !== '' ? rulesetId : container.ruleset_id
        }
        this.idsService.updateContainer(data)
          .subscribe(backendres => {
              container.description = res.description;
              container.configuration_id = configId;
              container.ruleset_id = rulesetId;
            },
            err => {
              this.errorPopup.showError(err.error["error"], err.status);
          })


        // TODO 0: update or refetch the ensembleContainers as well
      }
    })

  }

  removeEnsemble(ensembleToRemove: Ensemble){
    this.ensembleService.removeEnsemble(ensembleToRemove)
      .subscribe(backendres => {
          this.ensembleList = this.ensembleList.filter(ensemble => ensemble.id !== ensembleToRemove.id)
        },
        err =>  {
          this.errorPopup.showError(err.error["error"], err.status);
      })

  }

  remove(containerToRemove: Container){
    this.idsService.removeContainerById(containerToRemove.id)
      .subscribe(backendres => {
          this.containerList = this.containerList.filter(container => container !== containerToRemove);
        },
        err => {
          this.errorPopup.showError(err.error["error"], err.status);
      })

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

  getEnsembleTechniqueName(techniqueId: number){
    return this.ensembleTechniqueList.find(t => t.id == techniqueId)?.name;
  }

  containerIsIdle(container: Container){
    if(container.status !== statusTypes.idle){
      return false;
    }
    else{
      return true;
    }
  }


  containerIsActive(container: Container){
    if(container.status !== statusTypes.active){
      return false;
    }
    else{
      return true;
    }
  }


  containerIsSettingUp(container: Container){
    if(container.status !== statusTypes.setting_up){
      return false;
    }
    else{
      return true;
    }
  }

  ensembleIsIdle(ensemble: Ensemble){
    if(ensemble.status !== statusTypes.idle){
      return false;
    }
    else{
      return true;
    }
  }

  getEnsembleContainerFromEnsembleId(id: number){
    return this.ensembleContainerList.filter(e => e.ensemble_id == id);
  }

  getEnsembleContainerNamesFromEnsembleId(id: number){
    let ensembleContainer: EnsembleContainer[] = this.getEnsembleContainerFromEnsembleId(id);
    let containerIds = ensembleContainer.map(e => e.ids_container_id);
    return this.containerList.filter(c => containerIds.includes(c.id)).map(c => c.name);
  }

  checkEnsembleContainersAreIdleByEnsembleId(ensembleid: number){
    let ensembleContainerIds: number[] = this.getEnsembleContainerFromEnsembleId(ensembleid).map(c => c.ids_container_id);
    let containers: Container[] = this.containerList.filter(c => ensembleContainerIds.includes(c.id));
    let flag: boolean = true
    containers.forEach(container => {
      if(container.status !== statusTypes.idle){
        flag = false;
      }
    });
    return flag;
  }

  getHostName(id: number){
    return this.dockerHostList.find(host => host.id == id)?.name;
  }

  arrayEquals(a: Array<any>, b: Array<any>){
    return Array.isArray(a) &&
      Array.isArray(b) &&
      a.length === b.length &&
      a.every((val, index) => val === b[index]);
  }

}
