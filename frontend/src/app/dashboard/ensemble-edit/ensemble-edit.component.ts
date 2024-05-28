import { Component, Inject } from '@angular/core';
import { Ensemble, EnsembleContainer, EnsembleTechnqiue } from '../../models/ensemble';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { Container } from '../../models/container';

@Component({
  selector: 'app-ensemble-edit',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, FormsModule, MatInputModule, MatSelectModule, MatButtonModule, MatDialogModule],
  templateUrl: './ensemble-edit.component.html',
  styleUrl: './ensemble-edit.component.css'
})
export class EnsembleEditComponent {



  ngOnInit(): void {
    let selectedTechnique = this.getTechnique(this.data.ensemble.technique_id);
    let ensembleContainers: EnsembleContainer[] = [];
    ensembleContainers = this.data.ensembleContainerList.filter(ensembleContainer => ensembleContainer.ensemble_id == this.data.ensemble.id);

    let selectedContainers = this.getContainerIds(ensembleContainers).map(String);
    
    this.ensembleEdit.controls.ensembleTechnique.setValue(selectedTechnique.id.toString());
    this.ensembleEdit.controls.idsContainer.setValue(selectedContainers);
  }

  ensembleEdit = new FormGroup({
    description: new FormControl(this.data.ensemble.description),
    idsContainer: new FormControl(),
    ensembleTechnique: new FormControl(),
    name: new FormControl(this.data.ensemble.name)
  })





  constructor(
    public dialogRef: MatDialogRef<EnsembleEditComponent>,
    @Inject (MAT_DIALOG_DATA) public data: {
      ensemble: Ensemble,
      containerList: Container[],
      ensembleTechniqueList: EnsembleTechnqiue[],
      ensembleContainerList: EnsembleContainer[],
    }
  ) {}


  exit(): void{
    this.dialogRef.close();
  }

  saveChanges(): void{
    if(this.ensembleEdit.valid){
      this.dialogRef.close(this.ensembleEdit.value);
    }
  }

  getTechnique(techniqueId: number){
    return this.data.ensembleTechniqueList.filter(t => t.id == techniqueId)[0];
  }

  getContainerIds(ensembleContainerList: EnsembleContainer[]){
    let containerNames: number[] = [];
    for(var idx in ensembleContainerList){
      containerNames.push(this.data.containerList.filter(container => container.id == ensembleContainerList[idx].ids_container_id)[0].id)
    }
    return containerNames;
  }

}
