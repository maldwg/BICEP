import { Component, ViewChild, OnInit } from '@angular/core';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ConfigComponent } from '../config.component';
import { Dialog } from '@angular/cdk/dialog';
import { ConfigurationSetupData} from '../../models/configuration';
import { fileTypes, getAcceptedFileTypesForConfigurationType } from '../../models/acceptedFileTypes';
import { MatIconModule } from '@angular/material/icon';
import { ConfigService } from '../../services/config/config.service';
import { MatSelectModule } from '@angular/material/select';
import { CommonModule } from '@angular/common';
import { HttpEvent, HttpEventType } from '@angular/common/http';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import { DatasetSetupData } from '../../models/dataset';
import { DatasetService } from '../../services/dataset/dataset.service';
import { AlertComponent } from '../../components/alert-component/alert-component.component';
import { DatasetTypesService } from '../../services/dataset-type/dataset-type.service';
import { DatasetType } from '../../models/datasetType';
@Component({
    selector: 'app-config-creation',
    imports: [
        MatProgressBarModule,
        MatFormFieldModule,
        MatSelectModule,
        MatInputModule,
        FormsModule,
        ReactiveFormsModule,
        MatButtonModule,
        MatDialogTitle,
        MatDialogContent,
        MatDialogActions,
        MatDialogClose,
        MatDialogModule,
        MatIconModule,
        CommonModule,
        AlertComponent
    ], templateUrl: './config-creation.component.html',
    styleUrl: './config-creation.component.css'
})
export class ConfigCreationComponent implements OnInit{
  @ViewChild(AlertComponent) errorPopup!: AlertComponent;
  fileTypeList: string[] = [];
  datasetTypeList: DatasetType[] = [];
  selectedDatasetFileName: string = "";
  selectedLabelsFileName: string ="";
  selectedConfigurationFileName: string = "";

  configForm = new FormGroup({
    name: new FormControl(""),
    description: new FormControl(""),
    fileType: new FormControl(""),
    configurationFile: new FormControl(),
    dataFile: new FormControl(),
    labelsFile: new FormControl(),
    datasetTypeId: new FormControl(""),
  });

  fileNames: string[] = [];
  uploadProgress = 0;

  constructor(
    public dialogRef: MatDialogRef<ConfigCreationComponent>, 
    private configService: ConfigService,
    private datasetService: DatasetService,
    private datasetTypeService: DatasetTypesService,
  ){}

  ngOnInit(): void {
    this.getAllFileTypes();
    this.getAllDatasetTypes();

  }

 // 10: Polish: add a configrm dialog fro all delete actions to confirm if it should be delted
// Todo 10: polish: Add error cards to display errors as popup
// TODO 10: spinning circle while upload complete but not ready calcuating dataset
// TODO 10: return is there from the backend however, it is not processed correctly for the reload in the FE
  save(): void{
    if(this.configForm.value.fileType !== null){
      if(!this.check_if_necessary_files_are_attached(this.configForm.value.fileType!)){
        this.errorPopup.showError("Please select all required files before hitting save!", 400)
      }
    }
    if (this.configForm.valid){
      if(this.configForm.value.fileType === fileTypes.testData){
        let newDataset: DatasetSetupData = {
          name: this.configForm.value.name!,
          description: this.configForm.value.description!,
          labels_file: this.configForm.value.labelsFile!,
          data_file: this.configForm.value.dataFile!,
          dataset_type_id: String(this.configForm.value.datasetTypeId),

        };
        this.datasetService.addDataset(newDataset)
          .subscribe((event: HttpEvent<any>) => {
            switch (event.type) {
              case HttpEventType.UploadProgress:
                if (event.total) {
                  this.uploadProgress = Math.round((100 * event.loaded) / event.total);
                }
                break;
              case HttpEventType.Response:
                this.dialogRef.close(this.configForm.value);
                break;
            }
          }, err => {
            this.errorPopup.showError(err.error["error"], err.status);
          });
      }
      else{
        // if it is not a dataset, it is a configuration/ruleset which can be handled indifferently
        let newConfiguration: ConfigurationSetupData = {
          name: this.configForm.value.name!,
          description: this.configForm.value.description!,
          configuration: this.configForm.value.configurationFile!,
          file_type: this.configForm.value.fileType!,
        };
        this.configService.addConfiguration(newConfiguration)
          .subscribe((event: HttpEvent<any>) => {
            switch (event.type) {
              case HttpEventType.UploadProgress:
                if (event.total) {
                  this.uploadProgress = Math.round((100 * event.loaded) / event.total);
                }
                break;
              case HttpEventType.Response:
                this.dialogRef.close(this.configForm.value);
                break;
            }
          }, err => {
            this.errorPopup.showError(err.error["error"], err.status);
          });
      }
    }
  }

  check_if_necessary_files_are_attached(fileType: string): boolean{
    if(this.configForm.value.fileType === fileTypes.testData){
      if(this.configForm.value.dataFile && this.configForm.value.labelsFile){
        return true;
      }
    }
    else if(this.configForm.value.fileType === fileTypes.configuration || this.configForm.value.fileType === fileTypes.ruleSet){
      if(this.configForm.value.configurationFile){
        return true;
      }
    }
    return false;
  }

  exit(): void{
    this.dialogRef.close();
  }

  onFileSelected(event: any, fileType: 'dataset' | 'labels' | 'configuration') {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      let file_to_upload = input.files[0]
      if (fileType === 'dataset') {
        this.selectedDatasetFileName = input.files[0].name;
        this.configForm.patchValue({dataFile:file_to_upload });
      } else if (fileType === 'labels') {
        this.selectedLabelsFileName = input.files[0].name;
        this.configForm.patchValue({labelsFile:file_to_upload });
      }
      else if (fileType === 'configuration'){
          this.selectedConfigurationFileName = input.files[0].name;
          this.configForm.patchValue({configurationFile:file_to_upload });
      }
    }
  } 

  getAllDatasetTypes(){
    this.datasetTypeService.getAllDatasetTypes()
      .subscribe(datasetTypes => this.datasetTypeList = datasetTypes)
  }

  getAllFileTypes(){
    this.configService.getAllFileTypes()
      .subscribe(data => this.fileTypeList = data)
  }


  getAcceptType(): string {
    return getAcceptedFileTypesForConfigurationType(this.configForm.controls.fileType.value!);
  }

}
