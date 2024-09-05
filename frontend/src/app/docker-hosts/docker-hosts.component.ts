import { Component, OnInit } from '@angular/core';
import { DockerHostService } from '../services/host/host.service';
import { DockerHostSystem } from '../models/host';
import { MatDialog } from '@angular/material/dialog';
import { HostCreationComponent } from './host-creation/host-creation.component';
import { MatCard, MatCardActions, MatCardContent, MatCardHeader, MatCardModule, MatCardTitle } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatButton, MatButtonModule } from '@angular/material/button';
import { HttpResponse } from '@angular/common/http';

@Component({
  selector: 'app-hosts',
  standalone: true,
  imports: [
    MatCardModule,
    MatButtonModule,
    CommonModule
  ],
  templateUrl: './docker-hosts.component.html',
  styleUrl: './docker-hosts.component.css'
})
export class DockerHostsComponent implements OnInit{

  constructor (
    private hostService: DockerHostService,
    public dialog: MatDialog
  ) {}


  hostSystemList: DockerHostSystem[] = []

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
          docker_port: hostSystem.docker_port
        }))
      }
    )
  }


  removeHost(host: DockerHostSystem){
    this.hostService.removeHost(host.id).subscribe((response: HttpResponse<any>) => {
      if(response.status == 204){
        this.hostSystemList = this.hostSystemList.filter(h => h.id != host.id)
      } 
      else{
        console.error(response)
      }
    })

  }

  newHost(): void{
    const dialogRef = this.dialog.open(HostCreationComponent, {
      width: "50%",
      height: "50%",
    });

    dialogRef.afterClosed().subscribe(hostData =>{
      if(hostData !== null){
        console.log(hostData)
        	this.hostService.addHost(hostData).subscribe((result: HttpResponse<any>) => {
            if(result.status == 200){
              window.location.reload()
            }
            else{
              console.error(result)
            }            
          })
      }
      else {
        console.error("The addition was aborted")
      }
  })




  }

}
