import { Component, OnInit, ViewChild } from '@angular/core';
import { DockerHostService } from '../services/host/host.service';
import { DockerHostSystem } from '../models/host';
import { MatDialog } from '@angular/material/dialog';
import { HostCreationComponent } from './host-creation/host-creation.component';
import {  MatCardModule } from '@angular/material/card';

import { MatButton, MatButtonModule } from '@angular/material/button';
import { HttpResponse } from '@angular/common/http';
import { AlertComponent } from "../components/alert-component/alert-component.component";
import { hostStatus } from '../models/status';
import { MatIconModule } from '@angular/material/icon';

@Component({
    selector: 'app-hosts',
    imports: [
    MatCardModule,
    MatButtonModule,
    AlertComponent,
    MatIconModule
],
    templateUrl: './docker-hosts.component.html',
    styleUrl: './docker-hosts.component.scss'
})
export class DockerHostsComponent implements OnInit{
  @ViewChild(AlertComponent) errorPopup!: AlertComponent;
  constructor (
    private hostService: DockerHostService,
    public dialog: MatDialog
  ) {}


  hostSystemList: DockerHostSystem[] = []
  hostStatus = hostStatus
  ngOnInit(): void {
    this.getAllHostSystems()

  }


  getAllHostSystems(){
    this.hostService.getAllHosts().subscribe(
      hostSystems => {
        this.hostSystemList = hostSystems.map(hostSystem => ({
          id: hostSystem.id,
          name: hostSystem.name,
          host: hostSystem.host,
          docker_port: hostSystem.docker_port,
          status: hostSystem.status
        }))
      }
    )
  }


  removeHost(host: DockerHostSystem){
    this.hostService.removeHost(host.id).subscribe(response => {
        this.hostSystemList = this.hostSystemList.filter(h => h.id != host.id)
      },
      err => {
        this.errorPopup.showError(err.error["error"], err.status);
      })

  }

  newHost(): void{
    const dialogRef = this.dialog.open(HostCreationComponent, {
      width: "50%",
      height: "50%",
      panelClass: "matdialog-panel",
      backdropClass: "matdialog-backdrop"

    });

    dialogRef.afterClosed().subscribe(hostData =>{
      if(hostData !== null){
        console.log(hostData)
        	this.hostService.addHost(hostData).subscribe(result => {
              window.location.reload()
            },
            err => {
              this.errorPopup.showError(err.error["error"], err.status);
          })
      }
      else {
        console.error("The addition was aborted")
      }
  })




  }

}
