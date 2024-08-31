import { Component, Inject, OnInit } from '@angular/core';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ConfigComponent } from '../config.component';
import { Dialog } from '@angular/cdk/dialog';
import { ConfigurationSetupData, fileTypes } from '../../models/configuration';
import { MatIconModule } from '@angular/material/icon';
import { ConfigService } from '../../services/config/config.service';
import { MatSelectModule } from '@angular/material/select';
import { CommonModule } from '@angular/common';
import { HttpEvent, HttpEventType } from '@angular/common/http';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import { DatasetSetupData } from '../../models/dataset';
import { DatasetService } from '../../services/dataset/dataset.service';

@Component({
  selector: 'app-config-creation',
  standalone: true,
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
    CommonModule
  ],  templateUrl: './config-creation.component.html',
  styleUrl: './config-creation.component.css'
})
export class ConfigCreationComponent implements OnInit{

  fileTypeList: string[] = [];

  configForm = new FormGroup({
    name: new FormControl(""),
    description: new FormControl(""),
    configuration: new FormControl(),
    fileType: new FormControl(""),
  });

  fileNames: string[] = [];
  uploadProgress = 0;

  constructor(
    public dialogRef: MatDialogRef<ConfigCreationComponent>, 
    private configService: ConfigService,
    private datasetService: DatasetService,
  ){}

  ngOnInit(): void {
    this.getAllFileTypes();

  }

 // 10: Polish: add a configrm dialog fro all delete actions to confirm if it should be delted
// Todo 10: polish: Add error cards to display errors as popup
// TODO 10: spinning circle while upload complete but not ready calcuating dataset
// TODO 10: return is there from the backend however, it is not processed correctly for the reload in the FE
  save(): void{
    if (this.configForm.valid){
      if(this.configForm.value.fileType === fileTypes.testData){
        let newDataset: DatasetSetupData = {
          name: this.configForm.value.name!,
          description: this.configForm.value.description!,
          configuration: this.configForm.value.configuration!,
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
                console.log("Recorded event");
                this.dialogRef.close(this.configForm.value);
                console.log("close");
                break;
            }
          }, error => {
            console.error(error);
          });
      }
      else{
        let newConfiguration: ConfigurationSetupData = {
          name: this.configForm.value.name!,
          description: this.configForm.value.description!,
          configuration: this.configForm.value.configuration!,
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
                console.log("Recorded event");
                this.dialogRef.close(this.configForm.value);
                console.log("close");
                break;
            }
          }, error => {
            console.error(error);
          });
      }
    }
  }

  exit(): void{
    this.dialogRef.close();
  }

  onFileSelected(event: any) {
    const files:File[] = event.target.files;
    console.log(files)
    if (files && files.length > 0) {
        this.fileNames = Array.from(files).map(file => file.name);
        this.configForm.patchValue({configuration: files});
      }

}

getAllFileTypes(){
  this.configService.getAllFileTypes()
    .subscribe(data => this.fileTypeList = data)
}


getAcceptType(): string {
  switch (this.configForm.controls.fileType.value) {
    case fileTypes.testData:
      return '.pcap,.csv,.pcap_ISX';
    case fileTypes.configuration:
      return '.yaml,.conf,.json';
    case fileTypes.ruleSet:
      return '.rules';
    default:
      return '*/*';
  }
}

}
