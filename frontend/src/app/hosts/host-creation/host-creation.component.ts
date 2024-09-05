import { Component } from '@angular/core';
import { MatDialogActions, MatDialogClose, MatDialogContent, MatDialogModule, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { HostsComponent } from '../hosts.component';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import {HostSystemCreationData} from "../../models/host"
import { MatFormField, MatFormFieldModule, MatLabel } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
@Component({
  selector: 'app-host-creation',
  standalone: true,
  imports: [
    MatFormFieldModule,
    MatInputModule,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatIconModule,
    CommonModule
  ],
  templateUrl: './host-creation.component.html',
  styleUrl: './host-creation.component.css'
})
export class HostCreationComponent {


  hostForm = new FormGroup({
    name: new FormControl(""),
    host: new FormControl(""),
    dockerPort: new FormControl("2375"),
  })
  constructor(

    public dialogRef: MatDialogRef<HostCreationComponent>
  ) {

  }


  save() {
    if(this.hostForm.valid){
      let hostCreationData: HostSystemCreationData = {
        name: this.hostForm.value.name!,
        host: this.hostForm.value.host!,
        docker_port: parseInt(this.hostForm.value.dockerPort!)
      }
      this.dialogRef.close(hostCreationData)
    }
  }


  exit(){
    this.dialogRef.close(null);
  }
}
