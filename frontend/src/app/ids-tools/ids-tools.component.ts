import { Component, OnInit, ViewChild } from '@angular/core';
import { IdsService } from '../services/ids/ids.service';
import { IdsTool, IdsToolCreateData, IdsToolUpdateData } from '../models/ids';
import { MatDialog } from '@angular/material/dialog';
import { IdsToolDialogComponent } from './ids-tool-dialog/ids-tool-dialog.component';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { AlertComponent } from '../components/alert-component/alert-component.component';

@Component({
    selector: 'app-ids-tools',
    imports: [
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        CommonModule,
        AlertComponent
    ],
    templateUrl: './ids-tools.component.html',
    styleUrl: './ids-tools.component.scss'
})
export class IdsToolsComponent implements OnInit {
    @ViewChild(AlertComponent) errorPopup!: AlertComponent;
    toolList: IdsTool[] = [];

    constructor(
        private idsService: IdsService,
        public dialog: MatDialog
    ) { }

    ngOnInit(): void {
        this.getAllTools();
    }

    getAllTools(): void {
        this.idsService.getAllIdsTools().subscribe(tools => {
            this.toolList = tools;
        });
    }

    newTool(): void {
        const dialogRef = this.dialog.open(IdsToolDialogComponent, {
            width: 'min(94vw, 46rem)',
            maxWidth: '94vw',
            maxHeight: '88vh',
            backdropClass: 'bDrop',
            data: { mode: 'create' }
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result != null) {
                let toolData: IdsToolCreateData = {
                    name: result.name,
                    ids_type: result.ids_type,
                    analysis_method: result.analysis_method,
                    requires_ruleset: result.requires_ruleset,
                    image_name: result.image_name,
                    image_tag: result.image_tag,
                    deployment_type: result.deployment_type,
                    required_env_vars: result.required_env_vars || ''
                };
                this.idsService.addIdsTool(toolData).subscribe(
                    res => {
                        this.getAllTools();
                    },
                    err => {
                        this.errorPopup.showError(err.error['error'], err.status);
                    }
                );
            }
        });
    }

    editTool(tool: IdsTool): void {
        const dialogRef = this.dialog.open(IdsToolDialogComponent, {
            width: 'min(94vw, 46rem)',
            maxWidth: '94vw',
            maxHeight: '88vh',
            backdropClass: 'bDrop',
            data: { mode: 'edit', tool: tool }
        });

        dialogRef.afterClosed().subscribe(result => {
            if (result != null) {
                let toolData: IdsToolUpdateData = {
                    id: tool.id,
                    name: result.name,
                    ids_type: result.ids_type,
                    analysis_method: result.analysis_method,
                    requires_ruleset: result.requires_ruleset,
                    image_name: result.image_name,
                    image_tag: result.image_tag,
                    deployment_type: result.deployment_type,
                    required_env_vars: result.required_env_vars || ''
                };
                this.idsService.updateIdsTool(toolData).subscribe(
                    res => {
                        this.getAllTools();
                    },
                    err => {
                        this.errorPopup.showError(err.error['error'], err.status);
                    }
                );
            }
        });
    }

    removeTool(tool: IdsTool): void {
        this.idsService.deleteIdsTool(tool.id).subscribe(
            res => {
                this.toolList = this.toolList.filter(t => t.id !== tool.id);
            },
            err => {
                this.errorPopup.showError(err.error['error'], err.status);
            }
        );
    }

    getDeploymentLabel(type: string): string {
        switch (type) {
            case 'SINGLE_CONTAINER': return 'Single Container';
            case 'DOCKER_COMPOSE': return 'Docker Compose';
            default: return type;
        }
    }
}
