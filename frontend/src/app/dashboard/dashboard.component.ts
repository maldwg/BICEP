import { Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { NavbarComponent } from '../components/navbar/navbar.component';
import { IdsService } from '../services/ids/ids.service';
import { Container } from '../models/container';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [NavbarComponent, MatCardModule, CommonModule, MatButtonModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {

  containerList: Container[] = [];

  constructor (
    private idsService: IdsService,
    
  ) {}

  ngOnInit(): void {
    this.getAllContainer()
  }

  getAllContainer(): void{
    this.idsService.getAllIdsContainer()
      .subscribe(data =>  {
        this.containerList = data.map(container => ({
          id: container.id,
          host: container.host,
          port: container.port,
          status: container.status,
          description: container.description,
          configurationId: container.configurationId,
          idsTooId: container.idsTooId 
        }));
      });
  }

  edit(){
    
  }

  remove(containerToRemove: Container){
    this.idsService.removeContainerById(containerToRemove.id)
      .subscribe(() => console.log("Deleted item with id " + containerToRemove.id + " successfully"));
    this.containerList = this.containerList.filter(container => container !== containerToRemove);

  }

}
