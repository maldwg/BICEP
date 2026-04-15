import { Component, Inject, OnInit } from '@angular/core';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { ComposeService, Container, ContainerUpdateData } from '../../models/container';

import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { Configuration } from '../../models/configuration';
import { fileTypes } from '../../models/acceptedFileTypes';
import { MatButtonModule } from '@angular/material/button';
import { IdsTool } from '../../models/ids';
import { MatIconModule } from '@angular/material/icon';
import { ConfigService } from '../../services/config/config.service';

@Component({
  selector: 'app-ids-edit',
  imports: [ReactiveFormsModule, FormsModule, MatInputModule, MatSelectModule, MatCardModule, MatButtonModule, MatDialogModule, MatIconModule],
  templateUrl: './ids-edit.component.html',
  styleUrl: './ids-edit.component.scss'
})
export class IdsEditComponent implements OnInit {

  selectedIdsTool: IdsTool = {
    id: 0,
    name: "",
    analysis_method: "",
    ids_type: 'host',
    requires_ruleset: false,
    image_name: '',
    image_tag: '',
    deployment_type: 'SINGLE_CONTAINER',
    required_env_vars: ''
  };


  selectedRuleset: Configuration | undefined;

  configurationList: Configuration[] = [];
  rulesetList: Configuration[] = [];
  runtimeConfigList: Configuration[] = [];
  composeServicesByName: Record<string, ComposeService> = {};

  ngOnInit(): void {
    this.selectedIdsTool = this.data.idsToolList.find(t => t.id == this.data.container.ids_tool_id)!;
    let selectedConfiguration = this.data.configList.find(c => c.id == this.data.container.configuration_id);
    this.selectedRuleset = this.data.configList.find(c => c.id == this.data.container.ruleset_id);

    this.runtimeConfigList = this.data.configList.filter(c => c.file_type == fileTypes.runtime);
    this.rulesetList = this.data.configList.filter(r => r.file_type == fileTypes.ruleSet);

    if (this.selectedIdsTool.deployment_type === 'SINGLE_CONTAINER') {
        this.configurationList = this.runtimeConfigList;
    } else {
        this.configurationList = this.data.configList.filter(c => c.file_type == fileTypes.deployment);
    }

    // For CIDS, the config dropdown is hidden so remove its required validator
    const isCids = this.data.container.type?.toUpperCase() === 'CIDS';
    if (isCids) {
        this.idsEdit.controls.config.clearValidators();
        this.idsEdit.controls.config.updateValueAndValidity();

        if (this.data.container.configuration_id) {
          this.configService.getConfigurationServices(this.data.container.configuration_id).subscribe((services) => {
            this.composeServicesByName = services.reduce<Record<string, ComposeService>>((acc, service) => {
              acc[service.name] = service;
              return acc;
            }, {});
            this.normalizeComponentRuntimeConfigs();
          });
        }
    }

    if (selectedConfiguration) {
        this.idsEdit.controls.config.setValue(selectedConfiguration.id.toString());
    }
    if (this.selectedRuleset) {
        this.idsEdit.controls.ruleset.setValue(this.selectedRuleset.id.toString())
    }
  }

  idsEdit = new FormGroup({
    description: new FormControl(this.data.container.description),
    config: new FormControl(""),
    ruleset: new FormControl(""),
  })





  constructor(
    public dialogRef: MatDialogRef<IdsEditComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { container: Container, configList: Configuration[], idsToolList: IdsTool[] },
    private configService: ConfigService,
  ) { }


  exit(): void {
    this.dialogRef.close(null);
  }

  save(): void {
    if (this.idsEdit.valid) {
      const formValue = this.idsEdit.value;
      const updateData: ContainerUpdateData = {
        id: this.data.container.id,
        configuration_id: formValue.config ? parseInt(formValue.config) : this.data.container.configuration_id,
        ruleset_id: formValue.ruleset ? parseInt(formValue.ruleset) : (this.data.container.ruleset_id || undefined),
        description: formValue.description || "",
        components: this.data.container.components?.map(c => ({
          id: c.id,
          runtime_configuration_id: this.canEditRuntimeConfig(c) ? c.runtime_configuration_id : null,
          count: c.count
        }))
      };
      
      this.dialogRef.close(updateData);
    }
  }

  canEditRuntimeConfig(component: any): boolean {
    const serviceName = component?.service_name;
    if (!serviceName) {
      return false;
    }
    return !!this.composeServicesByName[serviceName]?.config_mount_path;
  }

  getRuntimeConfigHint(component: any): string {
    const serviceName = component?.service_name;
    const service = serviceName ? this.composeServicesByName[serviceName] : undefined;
    if (!service?.config_mount_path) {
      return 'No runtime config label on this service.';
    }
    if (service.expected_config_extension) {
      return `Mount target: ${service.config_mount_path} (expects ${service.expected_config_extension})`;
    }
    return `Mount target: ${service.config_mount_path}`;
  }

  private normalizeComponentRuntimeConfigs(): void {
    this.data.container.components?.forEach((component) => {
      if (!this.canEditRuntimeConfig(component)) {
        component.runtime_configuration_id = null;
      }
    });
  }

}
