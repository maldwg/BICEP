import { Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { NavbarComponent } from '../components/navbar/navbar.component';
import { IdsService } from '../services/ids/ids.service';
import { Container, ContainerUpdateData } from '../models/container';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { EnsembleService } from '../services/ensemble/ensemble.service';
import { Ensemble, EnsembleContainer, EnsembleTechnqiue, EnsembleUpdateData } from '../models/ensemble';
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
import { Configuration, fileTpyes } from '../models/configuration';
import { StartAnalysisComponent } from './start-analysis/start-analysis.component';
import { NetworkAnalysisData, NetworkAnalysisEnsembleData, StaticAnalysisData, StaticAnalysisEnsembleData, StopAnalysisData, StopAnalysisEnsembleData, analysisTypes } from '../models/analysis';
import { statusTypes } from '../models/status';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [NavbarComponent, MatCardModule, CommonModule, MatButtonModule, MatExpansionModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {

  containerList: Container[] = [];
  ensembleList: Ensemble[] = [];
  idsToolList: IdsTool[] = [];
  configList: Configuration[] = [];
  ensembleTechnqiueList: EnsembleTechnqiue[] = [];
  ensembleContainerList: EnsembleContainer[] = [];

  activeStatus = statusTypes.active;

  constructor (
    private idsService: IdsService,
    public idsDialog: MatDialog,
    public EnsembleDialog: MatDialog,
    public AnalysisDialog: MatDialog,
    private ensembleService: EnsembleService,
    private configService: ConfigService,
    
  ) {}

  ngOnInit(): void {
    this.getAllContainer();
    this.getAllEnsembles();
    this.getAllConfigs();
    this.getAllIdsTools();
    this.getAllTechnqiues();
    this.getAllEnsembleContainer();
  }

  getAllContainer(): void{
    this.idsService.getAllIdsContainer()
      .subscribe(data =>  {
        this.containerList = data.map(container => ({
          id: container.id,
          name: container.name,
          host: container.host,
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

  getAllTechnqiues(){
    this.ensembleService.getAllTechnqiues()
      .subscribe(data => {
        this.ensembleTechnqiueList = data.map(technqiue => ({
          id: technqiue.id,
          description: technqiue.description,
          name: technqiue.name
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
          requires_ruleset: tool.requires_ruleset
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
          description: ensemble.description
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

  startAnalysis(container: Container){
    const dialogRef = this.AnalysisDialog.open(StartAnalysisComponent, {
      height: "50%",
      width: "50%",
      data: {
        datasets: this.configList.filter(c => c.file_type == fileTpyes.testData)
      }
    })
    dialogRef.afterClosed().subscribe(res => {
      if(res.type === analysisTypes.static){
        let staticAnalysisData: StaticAnalysisData = {
          container_id: container.id,
          dataset_id: res.dataset
        }
        this.idsService.startStaticAnalysis(staticAnalysisData)
          .subscribe(backend_res => console.log(backend_res))
      }
      else if(res.type === analysisTypes.network){
        let networkAnalysisData: NetworkAnalysisData = {
          container_id: container.id
        }

        // TODO: Refactor all endpoints like this to propagate backend errors/m,essages
        this.idsService.startNetworkAnalysis(networkAnalysisData)
          .subscribe(backend_res => console.log(backend_res))
      }  
    })
  }

  stopAnalysis(container: Container){
    let stopData: StopAnalysisData = {
      container_id: container.id
    }
    this.idsService.stopAnalysis(stopData)
      .subscribe(res => console.log(res))
  }


  startEnsembleAnalysis(ensemble: Ensemble){
    const dialogRef = this.AnalysisDialog.open(StartAnalysisComponent, {
      height: "50%",
      width: "50%",
      data: {
        datasets: this.configList.filter(c => c.file_type == fileTpyes.testData)
      }
    })
    dialogRef.afterClosed().subscribe(res => {
      if(res.type === analysisTypes.static){
        let staticAnalysisData: StaticAnalysisEnsembleData = {
          ensemble_id: ensemble.id,
          dataset_id: res.dataset
        }
        this.ensembleService.startStaticAnalysis(staticAnalysisData)
          .subscribe(backend_res => console.log(backend_res))
      }
      else if(res.type === analysisTypes.network){
        let networkAnalysisData: NetworkAnalysisEnsembleData = {
          ensemble_id: ensemble.id
        }
        this.ensembleService.startNetworkAnalysis(networkAnalysisData)
          .subscribe(backend_res => console.log(backend_res))
      }
    })
  }

  stopEnsembleAnalysis(ensemble: Ensemble){
    let stopData: StopAnalysisEnsembleData = {
      ensemble_id: ensemble.id
    }
    this.ensembleService.stopAnalysis(stopData)
      .subscribe(res => console.log(res))
  }


  editEnsemble(ensemble: Ensemble){
    const dialogRef = this.EnsembleDialog.open(EnsembleEditComponent, {
      height: "50%",
      width: "50%",
      data: {
        ensemble: ensemble,
        containerList: this.containerList,
        ensembleTechniqueList: this.ensembleTechnqiueList,
        ensembleContainerList: this.ensembleContainerList
      }
    });
    dialogRef.afterClosed().subscribe(res => {
      console.log(res);
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
      let configId = parseInt(res.config);
      let rulesetId = parseInt(res.ruleset);
      if(
        res.description !== container.description ||
        configId !== container.configuration_id ||
        rulesetId !== container.ruleset_id
      ){
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

        // TODO: update or refetch the ensembleContainers as well
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

  getIdsToolName(toolId: number) {
    return this.idsToolList.find(t => t.id == toolId)?.name;
  }

  getEnsembleTechniqueName(techniqueId: number){
    return this.ensembleTechnqiueList.find(t => t.id == techniqueId)?.name;
  }
}
