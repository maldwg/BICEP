import { Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { ConfigService } from '../services/config/config.service';
import { Configuration, ConfigurationSetupData, fileTypes } from '../models/configuration';
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
import { DatasetService } from '../services/dataset/dataset.service';
import { Dataset } from '../models/dataset';
import { MatExpansionModule } from '@angular/material/expansion';
@Component({
  selector: 'app-config',
  standalone: true,
  imports: [ MatCardModule, MatButtonModule, CommonModule, MatExpansionModule],
  templateUrl: './config.component.html',
  styleUrl: './config.component.css'
})
export class ConfigComponent implements OnInit{

  configurationList: Configuration[] = [];
  datasetList: Dataset[] = [];
  fileTypeDict = fileTypes;

  constructor(
    private configService: ConfigService,
    private datasetService: DatasetService,
    public dialog: MatDialog,
  ) {  }

  ngOnInit(): void {
    this.getAllConfigs();
    this.getAllDatasets();
  }

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


  removeConfiguration(configuration: Configuration){
    this.configService.removeConfiguration(configuration.id)
      .subscribe(() => console.log("Removed configuration"));
    this.configurationList = this.configurationList.filter(config => config !== configuration);
  }
  removeDataset(dataset: Dataset){
    this.datasetService.removeDataset(dataset.id)
      .subscribe(() => console.log("Removed dataset"));
    this.datasetList = this.datasetList.filter(d => d !== dataset);
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
