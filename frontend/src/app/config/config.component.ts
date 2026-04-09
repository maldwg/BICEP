import { Component, OnChanges, OnInit, ViewChild } from '@angular/core';
import { ConfigService } from '../services/config/config.service';
import { Configuration, ConfigurationSetupData } from '../models/configuration';
import { fileTypes } from '../models/acceptedFileTypes';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon, MatIconModule } from '@angular/material/icon';

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
import { Router } from '@angular/router';
import { DatasetService } from '../services/dataset/dataset.service';
import { Dataset } from '../models/dataset';
import { MatExpansionModule } from '@angular/material/expansion';
import { AlertComponent } from '../components/alert-component/alert-component.component';
import { HttpResponse } from '@angular/common/http';
import { DatasetType } from '../models/datasetType';
import { DatasetTypesService } from '../services/dataset-type/dataset-type.service';


@Component({
    selector: 'app-config',
    imports: [MatCardModule, MatButtonModule, MatExpansionModule, AlertComponent, MatIconModule],
    templateUrl: './config.component.html',
    styleUrl: './config.component.scss'
})
export class ConfigComponent implements OnInit{
  @ViewChild(AlertComponent) errorPopup!: AlertComponent;

  configurationList: Configuration[] = [];
  datasetList: Dataset[] = [];
  fileTypeDict = fileTypes;
  datasetTypeList: DatasetType[] = [];

  constructor(
    private configService: ConfigService,
    private datasetService: DatasetService,
    private datasetTypeService: DatasetTypesService,
    public dialog: MatDialog,
  ) {  }

  ngOnInit(): void {
    this.getAllConfigs();
    this.getAllDatasets();
    this.getAllDatasetTypes();
  }

  getAllConfigs(){
    this.configService.getAllConfigurations()
      .subscribe(data => {
        this.configurationList = data
      });
    }


    getAllDatasets(){
      this.datasetService.getAllDatasets()
        .subscribe(dataset => this.datasetList = dataset);
        }

    getAllDatasetTypes(){
      this.datasetTypeService.getAllDatasetTypes()
        .subscribe(datasetType => this.datasetTypeList = datasetType)
    }


    getDatasetTypeName(id: number){
      return this.datasetTypeList.find(datasetType => datasetType.id == id)?.name
    }

  removeConfiguration(configuration: Configuration){
    this.configService.removeConfiguration(configuration.id)
      .subscribe(res => {
          this.configurationList = this.configurationList.filter(config => config !== configuration);
        },
        err => {
          this.errorPopup.showError(err.error["error"], err.status);
        });
  }
  removeDataset(dataset: Dataset){
    this.datasetService.removeDataset(dataset.id)
    .subscribe(res => {
        this.datasetList = this.datasetList.filter(d => d !== dataset);      
      },
      err => {
        this.errorPopup.showError(err.error["error"], err.status);
    });    
  }

  newConfig(): void {
    const dialogRef = this.dialog.open(ConfigCreationComponent, {
      height: '50%',
      width: '40%',
      panelClass: "matdialog-panel",
    });
 
    dialogRef.afterClosed().subscribe(res => {
      if (res != null) {
          window.location.reload();
      }      
    });
  }


}
