import { Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import {MatSelectModule} from '@angular/material/select';
import {MatInputModule} from '@angular/material/input';
import {MatFormFieldModule} from '@angular/material/form-field';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import {MatCardModule} from '@angular/material/card';
import {MatButtonModule} from '@angular/material/button';
import { IdsService } from '../services/ids/ids.service';
import { ConfigService } from '../services/config/config.service';
import { Router } from '@angular/router';
import { Container, ContainerSetupData } from '../models/container';
import { Configuration, fileTpyes } from '../models/configuration';
import { IdsTool } from '../models/ids';
import { CommonModule } from '@angular/common';
import { Ensemble, EnsembleSetupData, EnsembleTechnqiue } from '../models/ensemble';
import { EnsembleService } from '../services/ensemble/ensemble.service';
import { describe } from 'node:test';
import { runInThisContext } from 'node:vm';

@Component({
  selector: 'app-setup',
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, MatSelectModule, ReactiveFormsModule, MatCardModule, FormsModule, MatButtonModule, CommonModule ],
  templateUrl: './setup.component.html',
  styleUrl: './setup.component.css'
})
export class SetupComponent implements OnInit {
  //  TODO: add name to IDS creation
  idsForm = new FormGroup({
    host: new FormControl("localhost"),
    description: new FormControl(""),
    config: new FormControl(""),
    idsTool: new FormControl(""),
    ruleset: new FormControl(""),
  });

  ensembleForm = new FormGroup({
    name: new FormControl(""),
    description: new FormControl(""),
    containers: new FormControl(),
    technique: new FormControl(""),
  });

  idsConfigs: Configuration[] = [];
  ruleSets: Configuration[] = [];
  idsTools: IdsTool[] = [];
  containers: Container[] = [];
  ensembles: Ensemble[] = [];
  ensembleTechniques: EnsembleTechnqiue[] = [];
  userChoice = "";
  requiresRuleset = false;


  constructor(
    private idsService: IdsService,
    private configService: ConfigService,
    private ensembleService: EnsembleService,
    private router: Router,
  ) {}


  ngOnInit(): void {
   this.getAllIdsTools();
   this.getAllContainer();
   this.getAllEnemsebles();
   this.getAllTechniques();
   this.getConfigurations();
   this.getRuleSets();



   this.idsForm.controls.idsTool.valueChanges.subscribe((toolId) => {
    const selectedTool = this.idsTools.find(tool => tool.id == parseInt(toolId!));
    this.requiresRuleset = selectedTool ? selectedTool.requires_ruleset : false;
  }); 

  }

  onSubmit(): void {
    if (this.idsForm.valid){
      let containerData: ContainerSetupData = {
        host: this.idsForm.value.host!,
        ids_tool_id: parseInt(this.idsForm.value.idsTool!),
        configuration_id: parseInt(this.idsForm.value.config!),
        description: this.idsForm.value.description!,
        ruleset_id: this.idsForm.value.ruleset ? parseInt( this.idsForm.value.ruleset ) : undefined 
      };    
      this.idsService.sendContainerSetupData(containerData)
        .subscribe();
      this.router.navigate(["/"]);
    }
  }

  onEnsembleSubmit(){
    if(this.ensembleForm.valid){
      let ensembleData: EnsembleSetupData = {
        name: this.ensembleForm.value.name!,
        description: this.ensembleForm.value.description!,
        technique: parseInt(this.ensembleForm.value.technique!),
        container_ids: this.ensembleForm.value.containers!
      }
      console.log(this.ensembleForm)
      console.log(this.ensembleForm.value.containers);
      this.ensembleService.sendEnsembleData(ensembleData)
        .subscribe(() => console.log("successfully send data"))
    }
      this.router.navigate(["/"])
  }

  getConfigurations() {
    let type: string = fileTpyes.configuration;
    this.configService.getAllConfigurationsByType(type)
      .subscribe(data => {
        this.idsConfigs = data.map(config => ({
          id: config.id, name: config.name, configuration: config.configuration, description: config.description, file_type: config.file_type
        })); 
      });
  }

  getRuleSets() {
    let type: string = fileTpyes.ruleSet;
    this.configService.getAllConfigurationsByType(type)
      .subscribe(data => {
        this.ruleSets = data.map(config => ({
          id: config.id, name: config.name, configuration: config.configuration, description: config.description, file_type: config.file_type
        })); 
      });
  }

  getAllIdsTools() {
    this.idsService.getAllIdsTools()
      .subscribe(data => {
        this.idsTools = data.map( tool => ({
          id: tool.id, name: tool.name, idsType: tool.idsType, analysis_method: tool.analysis_method, requires_ruleset: tool.requires_ruleset
        }));
      });
  }

  getAllContainer(){
    this.idsService.getAllIdsContainer()
      .subscribe(data => {
        this.containers = data.map(container => ({
          id: container.id,
          name: container.name,
          host: container.host,
          port: container.port,
          status: container.status,
          configuration_id: container.configuration_id,
          ids_tool_id: container.ids_tool_id,
          description: container.description,
          ruleset_id: container.ruleset_id
        }))
      })
  }


  getAllTechniques(){
    this.ensembleService.getAllTechnqiues()
      .subscribe(data => {
        this.ensembleTechniques = data.map(technique => ({
          id: technique.id,
          name: technique.name,
          description: technique.description
        }));
      });
  }

  getAllEnemsebles(){
    this.ensembleService.getAllEnsembles()
      .subscribe(data => {
        this.ensembles = data.map(ensemble => ({
          id: ensemble.id,
          name: ensemble.name,
          description: ensemble.description,
          technique_id: ensemble.technique_id,
          status: ensemble.status
        }));
      });
  }

  setUserChoice(choice: string){
    this.userChoice = choice;
  }

}
