import { Component, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { NavbarComponent } from '../components/navbar/navbar.component';
import { IdsService } from '../services/ids/ids.service';
import { Container } from '../models/container';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { EnsembleService } from '../services/ensemble/ensemble.service';
import { Ensemble } from '../models/ensemble';
import {MatExpansionModule} from '@angular/material/expansion';
import {
  MatDialog,
  MAT_DIALOG_DATA,
  MatDialogRef,
  MatDialogTitle,
  MatDialogContent,
  MatDialogActions,
  MatDialogClose,
} from '@angular/material/dialog';
import { IdsEditComponent } from './ids-edit/ids-edit.component';
import { EnsembleEditComponent } from './ensemble-edit/ensemble-edit.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [NavbarComponent, MatCardModule, CommonModule, MatButtonModule, MatExpansionModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {

  containerList: Container[] = [];
  ensembleList: Ensemble[] = [];

  constructor (
    private idsService: IdsService,
    public idsDialog: MatDialog,
    public EnsembleDialog: MatDialog,
    private ensembleService: EnsembleService
    
  ) {}

  ngOnInit(): void {
    this.getAllContainer();
    this.getAllEnsembles();
  }

  //  IDS TOOL ID an dconfig id are not displayed properly
  getAllContainer(): void{
    this.idsService.getAllIdsContainer()
      .subscribe(data =>  {
        this.containerList = data.map(container => ({
          id: container.id,
          name: container.name,
          host: container.host,
          port: container.port,
          status: container.status,
          description: container.description,
          configuration_id: container.configuration_id,
          ids_tool_id: container.ids_tool_id ,
          ruleset_id: container.ruleset_id
        }));
      });
  }

  getAllEnsembles(){
    this.ensembleService.getAllEnsembles()
      .subscribe(data => {
        this.ensembleList = data.map(ensemble => ({
          id: ensemble.id,
          name: ensemble.name,
          technique_id: ensemble.technique_id,
          status: ensemble.status,
          description: ensemble.description
        }));
      });
  }

  editEnsemble(ensemble: Ensemble){
    const dialogRef = this.EnsembleDialog.open(EnsembleEditComponent, {
      height: "50%",
      width: "50%",
      data: ensemble
    });
    dialogRef.afterClosed().subscribe(res => {
      console.log(res)
    })
  }

  edit(container: Container){
    const dialogRef = this.idsDialog.open(IdsEditComponent, {
      height: "50%",
      width: "50%",
      data: container
    });

    dialogRef.afterClosed().subscribe(res => {
      console.log(res)
    })

  }

  removeEnsemble(ensembleToRemove: Ensemble){
    this.ensembleService.removeEnsemble(ensembleToRemove)
      .subscribe(() => console.log("ordered removal"))
    this.ensembleList = this.ensembleList.filter(ensemble => ensemble.id !== ensembleToRemove.id)
  }

  remove(containerToRemove: Container){
    this.idsService.removeContainerById(containerToRemove.id)
      .subscribe(() => console.log("Deleted item with id " + containerToRemove.id + " successfully"));
    this.containerList = this.containerList.filter(container => container !== containerToRemove);

  }

}
