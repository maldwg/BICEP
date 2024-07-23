import { Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { ConfigService } from '../services/config/config.service';
import { Configuration, ConfigurationSetupData } from '../models/configuration';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { ConfigCreationComponent } from './config-creation/config-creation.component';
import {
  MatDialog,
  MAT_DIALOG_DATA,
  MatDialogRef,
  MatDialogTitle,
  MatDialogContent,
  MatDialogActions,
  MatDialogClose,
} from '@angular/material/dialog';
import { ReadVResult } from 'fs';
import { Router } from '@angular/router';
@Component({
  selector: 'app-config',
  standalone: true,
  imports: [ MatCardModule, MatButtonModule, CommonModule, ],
  templateUrl: './config.component.html',
  styleUrl: './config.component.css'
})
export class ConfigComponent implements OnInit{

  configurationList: Configuration[] = [];
  fileTypeList: string[] = [];

  constructor(
    private configService: ConfigService,
    public dialog: MatDialog,
  ) {  }

  ngOnInit(): void {
    this.getAllConfigs();
  }

  // TODO: POLISH: split into different types (on display with view cards)

  getAllConfigs(){
    this.configService.getAllConfigurations()
      .subscribe(data => {
        this.configurationList = data.map(config => ({
          id: config.id,
          name: config.name,
          description: config.description,
          configuration: config.configuration,
          file_type: config.file_type
        }));
      });
    }



  remove(configuration: Configuration){
    this.configService.removeConfiguration(configuration.id)
      .subscribe(() => console.log("Removed configuration"));
    this.configurationList = this.configurationList.filter(config => config !== configuration);
  }


  newConfig(): void {
    const dialogRef = this.dialog.open(ConfigCreationComponent, {
      height: '50%',
      width: '40%',
    });
 
    dialogRef.afterClosed().subscribe(res => {
      if (res != null) {
          window.location.reload();
      }      
    });
  }


}
