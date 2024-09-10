import { Component, Inject, OnInit } from '@angular/core';
import { ControlContainer, FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { Container } from '../../models/container';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { Configuration, fileTypes } from '../../models/configuration';
import { MatButtonModule } from '@angular/material/button';
import { IdsTool } from '../../models/ids';

@Component({
  selector: 'app-ids-edit',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, FormsModule, MatInputModule, MatSelectModule, MatCardModule, MatButtonModule, MatDialogModule],
  templateUrl: './ids-edit.component.html',
  styleUrl: './ids-edit.component.css'
})
export class IdsEditComponent implements OnInit{

  selectedIdsTool: IdsTool = {
    id: 0,
    name: "",
    analysis_method: "",
    idsType: "",
    requires_ruleset: false,
    image_name: "",
    image_tag: ""
  }

  
  selectedRuleset: Configuration = {
    id: 0,
    configuration: "",
    description: "",
    file_type: "",
    name: ""
  }

  configurationList: Configuration[] = [];
  rulesetList: Configuration[] = [];

  ngOnInit(): void {
    this.selectedIdsTool = this.data.idsToolList.filter(t => t.id == this.data.container.ids_tool_id)[0];
    let selectedConfiguration = this.data.configList.filter(c => c.id == this.data.container.configuration_id)[0];
    this.selectedRuleset = this.data.configList.filter(c => c.id == this.data.container.ruleset_id)[0];

    this.configurationList = this.data.configList.filter(c => c.file_type == fileTypes.configuration);
    this.rulesetList = this.data.configList.filter(r => r.file_type == fileTypes.ruleSet);

    this.idsEdit.controls.config.setValue(selectedConfiguration.id.toString());
    this.idsEdit.controls.ruleset.setValue(this.selectedRuleset.id.toString())
  }

  idsEdit = new FormGroup({
    description: new FormControl(this.data.container.description),
    config: new FormControl(""),
    ruleset: new FormControl(""),
  })





  constructor(
    public dialogRef: MatDialogRef<IdsEditComponent>,
    @Inject (MAT_DIALOG_DATA) public data: {container: Container, configList: Configuration[], idsToolList: IdsTool[]},
  ) {}


  exit(): void{
    this.dialogRef.close(null);
  }

  save(): void{
    if(this.idsEdit.valid){
      this.dialogRef.close(this.idsEdit.value);
      
    }
  }

}
