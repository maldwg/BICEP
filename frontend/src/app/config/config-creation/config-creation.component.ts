import { Component, Inject, OnInit } from '@angular/core';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ConfigComponent } from '../config.component';
import { Dialog } from '@angular/cdk/dialog';
import { ConfigurationSetupData } from '../../models/configuration';
import { MatIconModule } from '@angular/material/icon';
import { ConfigService } from '../../services/config/config.service';
import { MatSelectModule } from '@angular/material/select';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-config-creation',
  standalone: true,
  imports: [
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

  fileName="";

  constructor(
    public dialogRef: MatDialogRef<ConfigCreationComponent>, 
    private configService: ConfigService,
  ){}

  ngOnInit(): void {
    this.getAllFileTypes();

  }

  save(): void{
    if (this.configForm.valid){
      this.dialogRef.close(this.configForm.value)
    }
  }

  exit(): void{
    this.dialogRef.close();
  }

  onFileSelected(event: any) {
    console.log(event)
    const file:File = event.target.files[0];
    if (file) {
        this.fileName = file.name;
        this.configForm.patchValue({configuration: file});
    }
}

getAllFileTypes(){
  this.configService.getAllFileTypes()
    .subscribe(data => this.fileTypeList = data)
}

}
