import { Component, Inject } from '@angular/core';
import { Ensemble } from '../../models/ensemble';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'app-ensemble-edit',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, FormsModule, MatInputModule, MatSelectModule, MatButtonModule],
  templateUrl: './ensemble-edit.component.html',
  styleUrl: './ensemble-edit.component.css'
})
export class EnsembleEditComponent {

  ngOnInit(): void {
    console.log(this.data)
  }

  ensembleEdit = new FormGroup({

  })





  constructor(
    public dialogRef: MatDialogRef<EnsembleEditComponent>,
    @Inject (MAT_DIALOG_DATA) public data: Ensemble,
  ) {}


  exit(): void{
    this.dialogRef.close();
  }

  saveChanges(): void{
    
  }
}
