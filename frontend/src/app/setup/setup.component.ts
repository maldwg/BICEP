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
import { ContainerSetupData } from '../models/container';
import { Configuration } from '../models/configuration';
import { IdsTool } from '../models/ids';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-setup',
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, MatSelectModule, ReactiveFormsModule, MatCardModule, FormsModule, MatButtonModule, CommonModule ],
  templateUrl: './setup.component.html',
  styleUrl: './setup.component.css'
})
export class SetupComponent implements OnInit {
  idsForm = new FormGroup({
    host: new FormControl("localhost"),
    description: new FormControl(""),
    config: new FormControl(""),
    idsTool: new FormControl(""),
  });


  configurations: Configuration[] = [];
  idsTools: IdsTool[] = [];
  userChoice = "";


  constructor(
    private idsService: IdsService,
    private configService: ConfigService,
    private router: Router,
  ) {}

  ngOnInit(): void {
   this.getAllConfigs()
   this.getAllIdsTools()
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

  getAllConfigs() {
    this.configService.getAllConfigurations()
      .subscribe(data => {
        this.configurations = data.map(config => ({
          id: config.id, name: config.name, configuration: config.configuration, description: config.description
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

  setUserChoice(choice: string){
    this.userChoice = choice;
  }

}
