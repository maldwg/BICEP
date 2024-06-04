import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { Configuration, fileTpyes } from '../../models/configuration';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { analysisTypes } from '../../models/analysis';

@Component({
  selector: 'app-start-analysis',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, FormsModule, MatInputModule, MatSelectModule, MatCardModule, MatButtonModule, MatDialogModule],
  templateUrl: './start-analysis.component.html',
  styleUrl: './start-analysis.component.css'
})
export class StartAnalysisComponent implements OnInit{

  testDataType = analysisTypes.static;
  analysisTypes: string[] = [];

  analysisForm = new FormGroup({
    type: new FormControl(),
    dataset: new FormControl(),
  })

  constructor(
    public dialogRef: MatDialogRef<StartAnalysisComponent>,
    @Inject (MAT_DIALOG_DATA) public data: {datasets: Configuration[]},
  ) {}


  ngOnInit(): void {
    this.analysisTypes = Object.values(analysisTypes);
    
  }


  startAnalysis(){
    if(this.analysisForm.valid){
      this.dialogRef.close(this.analysisForm.value);
    }
  }

  exit(){
    this.dialogRef.close()
  }

}
