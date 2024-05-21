import { Component, OnInit } from '@angular/core';
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
@Component({
  selector: 'app-config',
  standalone: true,
  imports: [ MatCardModule, MatButtonModule, CommonModule, ],
  templateUrl: './config.component.html',
  styleUrl: './config.component.css'
})
export class ConfigComponent implements OnInit{

  configurationList: Configuration[] = [];

  constructor(
    private configService: ConfigService,
    public dialog: MatDialog
  ) {  }

  ngOnInit(): void {
    this.getAllConfigs();
  }


  getAllConfigs(){
    this.configService.getAllConfigurations()
      .subscribe(data => {
        this.configurationList = data.map(config => ({
          id: config.id,
          description: config.description,
          configuration: config.configuration
        }));
      });
    }

  remove(configuration: Configuration){
    this.configService.removeConfiguration(configuration.id);
    this.configurationList = this.configurationList.filter(config => config !== configuration);
  }


  newConfig(): void {
    const dialogRef = this.dialog.open(ConfigCreationComponent, {
      height: '50%',
      width: '40%',
    });

    dialogRef.afterClosed().subscribe(res => {
      if (res != null) {
        console.log("configuration: "+res.configuration)
        let newConfiguration: ConfigurationSetupData = {
          name: res.name,
          description: res.description,
          configuration: res.configuration
        };
        this.configService.addConfiguration(newConfiguration)
          .subscribe(() => console.log("Added configuration"));

      }
      console.log('The dialog was closed');
    });
  }


}
