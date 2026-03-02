import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { IdsTool } from '../../models/ids';

@Component({
    selector: 'app-ids-tool-dialog',
    imports: [
        MatFormFieldModule,
        MatInputModule,
        MatSelectModule,
        FormsModule,
        ReactiveFormsModule,
        MatButtonModule,
        MatDialogModule,
        MatIconModule,
        MatCheckboxModule
    ],
    templateUrl: './ids-tool-dialog.component.html',
    styleUrl: './ids-tool-dialog.component.scss'
})
export class IdsToolDialogComponent {

    isEditMode: boolean;

    nameControl: FormControl;
    idsTypeControl: FormControl;
    analysisMethodControl: FormControl;
    requiresRulesetControl: FormControl;
    imageNameControl: FormControl;
    imageTagControl: FormControl;
    deploymentTypeControl: FormControl;

    toolForm: FormGroup;

    idsTypes = ['NIDS', 'HIDS', 'CIDS'];
    analysisMethods = ['static', 'network', 'both'];
    deploymentTypes = ['SINGLE_CONTAINER', 'DOCKER_COMPOSE'];

    constructor(
        public dialogRef: MatDialogRef<IdsToolDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: { mode: string, tool?: IdsTool }
    ) {
        this.isEditMode = data.mode === 'edit';

        this.nameControl = new FormControl(this.isEditMode ? data.tool!.name : '');
        this.idsTypeControl = new FormControl(this.isEditMode ? data.tool!.ids_type : '');
        this.analysisMethodControl = new FormControl(this.isEditMode ? data.tool!.analysis_method : '');
        this.requiresRulesetControl = new FormControl(this.isEditMode ? data.tool!.requires_ruleset : false);
        this.imageNameControl = new FormControl(this.isEditMode ? data.tool!.image_name : '');
        this.imageTagControl = new FormControl(this.isEditMode ? data.tool!.image_tag : 'latest');
        this.deploymentTypeControl = new FormControl(this.isEditMode ? data.tool!.deployment_type : 'SINGLE_CONTAINER');

        this.toolForm = new FormGroup({
            name: this.nameControl,
            ids_type: this.idsTypeControl,
            analysis_method: this.analysisMethodControl,
            requires_ruleset: this.requiresRulesetControl,
            image_name: this.imageNameControl,
            image_tag: this.imageTagControl,
            deployment_type: this.deploymentTypeControl,
        });
    }

    save(): void {
        if (this.toolForm.valid) {
            this.dialogRef.close(this.toolForm.value);
        }
    }

    exit(): void {
        this.dialogRef.close(null);
    }
}
