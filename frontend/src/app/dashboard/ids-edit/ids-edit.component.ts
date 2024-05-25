import { Component, Inject, OnInit } from '@angular/core';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { Container } from '../../models/container';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { ConfigService } from '../../services/config/config.service';
import { Configuration } from '../../models/configuration';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-ids-edit',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, FormsModule, MatInputModule, MatSelectModule, MatCardModule, MatButtonModule],
  templateUrl: './ids-edit.component.html',
  styleUrl: './ids-edit.component.css'
})
export class IdsEditComponent implements OnInit{

  configurations: Configuration[] = [];
  currentConfig: Configuration = {
    id: 0,
    configuration: "",
    description: "",
    name: "",
    file_type: ""
  };

  ngOnInit(): void {
    console.log(this.data)
    this.getAllConfigs();
    this.currentConfig = this.configurations.filter(c => c.id === this.data.configurationId)[0];
  }

  idsEdit = new FormGroup({
    description: new FormControl(this.data.description),
    config: new FormControl(this.currentConfig.id)
  })





  constructor(
    public dialogRef: MatDialogRef<IdsEditComponent>,
    @Inject (MAT_DIALOG_DATA) public data: Container,
    private configService: ConfigService
  ) {}


  exit(): void{
    this.dialogRef.close();
  }

  saveChanges(): void{
    
  }

  getAllConfigs() {
    this.configService.getAllConfigurations()
      .subscribe(data => {
        this.configurations = data.map(config => ({
          id: config.id, name: config.name, configuration: config.configuration, description: config.description, file_type: config.file_type
        })); 
      });
  }
}
