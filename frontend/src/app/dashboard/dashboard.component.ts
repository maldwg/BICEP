import { Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { HttpClient, HttpResponse } from '@angular/common/http';
import { NavbarComponent } from '../components/navbar/navbar.component';
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
import { Configuration, fileTypes } from '../models/configuration';
import { StartAnalysisComponent } from './start-analysis/start-analysis.component';
import { NetworkAnalysisData, StaticAnalysisData, StopAnalysisData, analysisTypes } from '../models/analysis';
import { statusTypes } from '../models/status';
import { STATUS_CODES } from 'node:http';
import { DatasetService } from '../services/dataset/dataset.service';
import { Dataset } from '../models/dataset';
import { MatIconModule } from '@angular/material/icon';
import { DockerHostService } from '../services/host/host.service';
import { DockerHostSystem } from '../models/host';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [NavbarComponent, MatCardModule, CommonModule, MatButtonModule, MatExpansionModule, MatIconModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {

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
      .subscribe(data =>  {
        this.containerList = data.map(container => ({
          id: container.id,
          name: container.name,
          host_system_id: container.host_system_id,
          port: container.port,
          status: container.status,
          description: container.description,
          configuration_id: container.configuration_id,
          ids_tool_id: container.ids_tool_id ,
          ruleset_id: container.ruleset_id
        }));
      });
  }

  getAllConfigs(){
    this.configService.getAllConfigurations()
      .subscribe(data => {
        this.configList = data.map(config => ({
          id: config.id,
          name: config.name,
          configuration: config.configuration,
          description: config.description,
          file_type: config.file_type
        }));
      });
  }

  getAllDatasets(){
    this.datasetService.getAllDatasets()
      .subscribe(data => {
        this.datasetList = data.map(config => ({
          id: config.id,
          name: config.name,
          pcap_file_path: config.pcap_file_path,
          description: config.description,
          labels_file_path: config.labels_file_path,
          ammount_benign: config.ammount_benign,
          ammount_malicious: config.ammount_malicious,
        }));
      });
  }

  getAllTechnqiues(){
    this.ensembleService.getAllTechnqiues()
      .subscribe(data => {
        this.ensembleTechniqueList = data.map(technique => ({
          id: technique.id,
          description: technique.description,
          name: technique.name,
          function_name: technique.function_name
        }));
      });   
  }

  getAllIdsTools(){
    this.idsService.getAllIdsTools()
      .subscribe(data => {
        this.idsToolList = data.map(tool => ({
          id: tool.id,
          name: tool.name,
          analysis_method: tool.analysis_method,
          idsType: tool.idsType,
          requires_ruleset: tool.requires_ruleset,
          image_name: tool.image_name,
          image_tag: tool.image_tag
        }));
      });
  }

  getAllEnsembles(){
    this.ensembleService.getAllEnsembles()
      .subscribe(data => {
        this.ensembleList = data.map(ensemble => ({
          id: ensemble.id,
          name: ensemble.name,
          technique_id: ensemble.technique_id,
          status: ensemble.status,
          description: ensemble.description,
          current_analysis_id: ensemble.current_analysis_id,
        }));
      });
  }

  getAllEnsembleContainer(){
    this.ensembleService.getEnsembleContainers()  
      .subscribe(data => {
        this.ensembleContainerList = data.map( ensembleContainer => ({
          id: ensembleContainer.id,
          ensemble_id: ensembleContainer.ensemble_id,
          ids_container_id: ensembleContainer.ids_container_id
        }));
      });
  }

  // TODO 10: if not status code 200 then popup with error code 
  startAnalysis(container: Container){
    const dialogRef = this.AnalysisDialog.open(StartAnalysisComponent, {
      height: "50%",
      width: "50%",
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
          this.idsService.startStaticAnalysis(staticAnalysisData)
            .subscribe((backendRes: HttpResponse<any>) => {
              console.log(backendRes)
              if(backendRes.status === 200){
                console.log("success")
                container.status = statusTypes.active
              }
              else{
                console.log("not")
              }
            })
        }
        else if(res.type === analysisTypes.network){
          let networkAnalysisData: NetworkAnalysisData = {
            container_id: container.id
          }
  
          // TODO 10: Refactor all endpoints like this to propagate backend errors/m,essages
          this.idsService.startNetworkAnalysis(networkAnalysisData)
            .subscribe((backendRes: HttpResponse<any>) => {
              console.log(backendRes)
              if(backendRes.status === 200){
                container.status = statusTypes.active
              }
            })
        }  
      }
      else {
        console.log("Canceled analysis start");
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
  

  stopAnalysis(container: Container){
    let stopData: StopAnalysisData = {
      container_id: container.id
    }
    this.idsService.stopAnalysis(stopData)
      .subscribe((res: HttpResponse<any>) => {
        console.log(res)
        if(res.status == 200){
          container.status = statusTypes.idle
        }
      })
  }


  startEnsembleAnalysis(ensemble: Ensemble){
    const dialogRef = this.AnalysisDialog.open(StartAnalysisComponent, {
      height: "50%",
      width: "50%",
      data: {
        datasets: this.datasetList
      }
    })
    dialogRef.afterClosed().subscribe(res => {
      if(res != null){
        if(res.type === analysisTypes.static){
          let staticAnalysisData: StaticAnalysisData = {
            ensemble_id: ensemble.id,
            dataset_id: res.dataset
          }
          this.ensembleService.startStaticAnalysis(staticAnalysisData)
            .subscribe((backendRes: HttpResponse<any>) => {
              console.log(backendRes)
              if(backendRes.status === 200){
                ensemble.status = statusTypes.active
              }
            })
        }
        else if(res.type === analysisTypes.network){
          let networkAnalysisData: NetworkAnalysisData = {
            ensemble_id: ensemble.id
          }
          this.ensembleService.startNetworkAnalysis(networkAnalysisData)
            .subscribe((backendRes: HttpResponse<any>) => {
              console.log(backendRes)
              if(backendRes.status === 200){
                ensemble.status = statusTypes.active
                // TODO 5: update status of each container
              }
            })
        }
      }
      else {
        console.log("Canceled analysis start");
      }
    })
  }

  stopEnsembleAnalysis(ensemble: Ensemble){
    let stopData: StopAnalysisData = {
      ensemble_id: ensemble.id
    }
    this.ensembleService.stopAnalysis(stopData)
      .subscribe((res: HttpResponse<any>) => {
        console.log(res)
        if(res.status === 200){
          ensemble.status = statusTypes.idle
          // TODO 5: update containers to dile again 
        }
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
      }
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
          .subscribe(() => console.log("send update data for ensemble"));
        
        ensemble.name = ensembleUpdate.name;
        ensemble.description = ensembleUpdate.description;
        ensemble.technique_id = ensembleUpdate.technique_id;
        
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
      }
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
          .subscribe(() => console.log("Successfully send update"))

        container.description = res.description;
        container.configuration_id = configId;
        container.ruleset_id = rulesetId;

        // TODO 0: update or refetch the ensembleContainers as well
      }
    })

  }

  removeEnsemble(ensembleToRemove: Ensemble){
    this.ensembleService.removeEnsemble(ensembleToRemove)
      .subscribe(() => console.log("ordered removal"))
    this.ensembleList = this.ensembleList.filter(ensemble => ensemble.id !== ensembleToRemove.id)
  }

  remove(containerToRemove: Container){
    this.idsService.removeContainerById(containerToRemove.id)
      .subscribe(() => console.log("Deleted item with id " + containerToRemove.id + " successfully"));
    this.containerList = this.containerList.filter(container => container !== containerToRemove);

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
