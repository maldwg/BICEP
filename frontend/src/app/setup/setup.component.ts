import { Component, OnInit } from '@angular/core';
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

  }

  onSubmit(): void {
    if (this.idsForm.valid){
      let containerData: ContainerSetupData = {
        host: this.idsForm.value.host!,
        idsToolId: parseInt(this.idsForm.value.idsTool!),
        configurationId: parseInt(this.idsForm.value.config!),
        description: this.idsForm.value.description!,
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
      console.log(this.ensembleForm.value.containers);
      this.ensembleService.sendEnsembleData(ensembleData)
        .subscribe(() => console.log("successfully send data"))
    }
      this.router.navigate(["/"])
  }

  // getAllConfigs() {
  //   this.configService.getAllConfigurations()
  //     .subscribe(data => {
  //       this.configurations = data.map(config => ({
  //         id: config.id, name: config.name, configuration: config.configuration, description: config.description, file_type: config.file_type
  //       })); 
  //     });
  // }

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
          id: tool.id, name: tool.name, idsType: tool.idsType, analysisMethod: tool.analysisMethod
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
          configurationId: container.configurationId,
          idsToolId: container.idsToolId,
          description: container.description
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
          techniqueId: ensemble.techniqueId,
          status: ensemble.status
        }));
      });
  }

  setUserChoice(choice: string){
    this.userChoice = choice;
  }

}
