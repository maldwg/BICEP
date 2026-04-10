import { Component, OnInit, ViewChild } from '@angular/core';
import { DockerHostService } from '../services/host/host.service';
import { DockerHostSystem, RegisteredMetricService } from '../models/host';
import { MatDialog } from '@angular/material/dialog';
import { HostCreationComponent } from './host-creation/host-creation.component';
import {  MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { AlertComponent } from "../components/alert-component/alert-component.component";
import { hostStatus } from '../models/status';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
    selector: 'app-hosts',
    imports: [
    MatCardModule,
    MatButtonModule,
    AlertComponent,
    MatIconModule,
    MatTooltipModule
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
          status: hostSystem.status,
          status_message: hostSystem.status_message,
          metric_service: hostSystem.metric_service
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
      backdropClass: "bDrop"

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


  formatStatusLabel(status?: string | null): string {
    if (!status) {
      return 'Unknown';
    }

    return status
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, letter => letter.toUpperCase());
  }

  getHostStatusTooltip(host: DockerHostSystem): string {
    if (host.status === hostStatus.available) {
      return '';
    }

    return this.shortenStatusMessage(
      host.status_message || 'Docker host is unavailable.'
    );
  }

  getMetricServiceStatusTooltip(
    metricService?: RegisteredMetricService | null
  ): string {
    if (!metricService || metricService.status === hostStatus.available) {
      return '';
    }

    return this.shortenStatusMessage(
      metricService.status_message || this.getMetricServiceFallbackMessage(metricService.status)
    );
  }

  private getMetricServiceFallbackMessage(status?: string): string {
    switch (status) {
      case 'deploying':
        return 'Metric service is deploying.';
      case 'registering':
        return 'Metric service is registering.';
      case hostStatus.unavailable:
        return 'Metric service is unavailable.';
      default:
        return 'Metric service is not available.';
    }
  }

  private shortenStatusMessage(message: string, maxLength = 90): string {
    if (message.length <= maxLength) {
      return message;
    }

    return `${message.slice(0, maxLength - 3).trimEnd()}...`;
  }

}
