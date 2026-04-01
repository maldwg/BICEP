import { Component, OnInit, ViewChild } from '@angular/core';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { IdsService } from '../services/ids/ids.service';
import { ConfigService } from '../services/config/config.service';
import { Router } from '@angular/router';
import { Container, ContainerSetupData, CidsServiceConfig, ComposeService } from '../models/container';
import { Configuration } from '../models/configuration';
import { fileTypes } from '../models/acceptedFileTypes';
import { IdsTool } from '../models/ids';
import { CommonModule } from '@angular/common';
import { EnsembleSetupData, EnsembleTechnique } from '../models/ensemble';
import { EnsembleService } from '../services/ensemble/ensemble.service';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DockerHostService } from '../services/host/host.service';
import { DockerHostSystem } from '../models/host';
import { AlertComponent } from '../components/alert-component/alert-component.component';
import { hostStatus } from '../models/status';
import { MatIconModule } from '@angular/material/icon';
@Component({
  selector: 'app-setup',
  imports: [MatIconModule, AlertComponent, MatTooltipModule, MatFormFieldModule, MatInputModule, MatSelectModule, ReactiveFormsModule, MatCardModule, FormsModule, MatButtonModule, CommonModule],
  templateUrl: './setup.component.html',
  styleUrl: './setup.component.scss'
})
export class SetupComponent implements OnInit {

  hostStatus = hostStatus;
  @ViewChild(AlertComponent) errorPopup!: AlertComponent;
  idsForm = new FormGroup({
    host: new FormControl("localhost"),
    description: new FormControl(""),
    config: new FormControl(""),
    idsTool: new FormControl(""),
    ruleset: new FormControl(""),
  });

  ensembleForm = new FormGroup({
    name: new FormControl(""),
    description: new FormControl(""),
    containers: new FormControl(),
    technique: new FormControl(""),
  });

  filteredConfigs: Configuration[] = [];
  ruleSets: Configuration[] = [];
  idsTools: IdsTool[] = [];
  hostSystems: DockerHostSystem[] = [];
  containers: Container[] = [];
  ensembleTechniques: EnsembleTechnique[] = [];
  userChoice = "";
  requiresRuleset = false;

  // CIDS Support
  selectedTool: IdsTool | undefined;
  cidsConfigurations: CidsServiceConfig[] = [];
  availableServices: ComposeService[] = [];
  deploymentType = "SINGLE_CONTAINER";

  // CIDS Environment Variables
  cidsEnvVars: { key: string, value: string }[] = [];
  envVarKeyControl = new FormControl('');
  envVarValueControl = new FormControl('');

  // Runtime Configs available for selection
  runtimeConfigs: Configuration[] = [];
  deploymentConfigs: Configuration[] = [];

  cidsHostSelection = new FormControl();
  cidsServiceSelection = new FormControl();
  cidsCountSelection = new FormControl(1);

  constructor(
    private idsService: IdsService,
    private configService: ConfigService,
    private ensembleService: EnsembleService,
    private router: Router,
    private hostService: DockerHostService,
  ) { }


  ngOnInit(): void {
    this.getAllIdsTools();
    this.getAllContainer();
    this.getAllTechniques();
    this.getConfigurations();
    this.getRuleSets();
    this.getAllHostSystems();

    this.idsForm.controls.idsTool.valueChanges.subscribe((toolId) => {
      this.selectedTool = this.idsTools.find(tool => tool.id == parseInt(toolId!));
      this.requiresRuleset = this.selectedTool ? this.selectedTool.requires_ruleset : false;
      this.deploymentType = this.selectedTool?.deployment_type || "SINGLE_CONTAINER";

      // Filter configs based on deployment type
      if (this.deploymentType === 'DOCKER_COMPOSE') {
        this.filteredConfigs = this.deploymentConfigs;
      } else {
        this.filteredConfigs = this.runtimeConfigs;
      }
      // Reset config selection when tool changes
      this.idsForm.controls.config.reset();

      // Reset CIDS state on tool change
      this.cidsConfigurations = [];
      this.availableServices = [];

      // Auto-populate mandatory env vars from tool definition
      this.cidsEnvVars = [];
      if (this.selectedTool?.required_env_vars) {
        const vars = this.selectedTool.required_env_vars.split(',').map(v => v.trim()).filter(v => v);
        this.cidsEnvVars = vars.map(key => ({ key, value: '' }));
      }
    });

    // Listen for config changes to fetch services if CIDS
    this.idsForm.controls.config.valueChanges.subscribe((configId) => {
      if (this.deploymentType === 'DOCKER_COMPOSE' && configId) {
        this.configService.getConfigurationServices(parseInt(configId)).subscribe(services => {
          this.availableServices = services;

          // Auto-assign all services to the best available host (Core server preferred)
          const defaultHostId = this.getDefaultHostId();
          if (defaultHostId !== null) {
            this.cidsConfigurations = services.map(svc => ({
              host_system_id: defaultHostId,
              service_name: svc.name,
              count: 1,
              runtime_configuration_id: null,
              is_sensor: svc.is_sensor,
              config_mount_path: svc.config_mount_path,
              expected_config_extension: svc.expected_config_extension,
            }));
          }
        });
      } else if (this.deploymentType === 'DOCKER_COMPOSE') {
        this.availableServices = [];
        this.cidsConfigurations = [];
      }
    });

  }

  addCidsConfiguration() {
    if (this.cidsHostSelection.value && this.cidsServiceSelection.value) {
      const selectedSvc = this.availableServices.find(s => s.name === this.cidsServiceSelection.value);
      const newConfig: CidsServiceConfig = {
        host_system_id: parseInt(this.cidsHostSelection.value),
        service_name: this.cidsServiceSelection.value,
        count: this.cidsCountSelection.value || 1,
        runtime_configuration_id: null,
        is_sensor: selectedSvc ? selectedSvc.is_sensor : false,
        config_mount_path: selectedSvc?.config_mount_path,
        expected_config_extension: selectedSvc?.expected_config_extension,
      };
      this.cidsConfigurations.push(newConfig);
    }
  }

  removeCidsConfiguration(index: number) {
    this.cidsConfigurations.splice(index, 1);
  }

  updateCidsHostAssignment(index: number, hostId: number): void {
    this.cidsConfigurations[index].host_system_id = hostId;
  }

  updateCidsCount(index: number, event: Event): void {
    const value = parseInt((event.target as HTMLInputElement).value) || 1;
    this.cidsConfigurations[index].count = Math.max(1, value);
  }

  updateCidsRuntimeConfig(index: number, configId: string | number | null): void {
    if (!this.cidsConfigurations[index].config_mount_path) {
      this.cidsConfigurations[index].runtime_configuration_id = null;
      return;
    }
    if (configId === null || configId === undefined || configId === '') {
      this.cidsConfigurations[index].runtime_configuration_id = null;
      return;
    }
    this.cidsConfigurations[index].runtime_configuration_id = parseInt(String(configId));
  }

  hasRuntimeConfigMount(config: CidsServiceConfig): boolean {
    return !!config.config_mount_path;
  }

  getRuntimeConfigHint(config: CidsServiceConfig): string {
    if (!config.config_mount_path) {
      return 'No bicep.config.mount label on this service. Leave runtime config set to None.';
    }
    if (config.expected_config_extension) {
      return `Mount target: ${config.config_mount_path} (expects ${config.expected_config_extension})`;
    }
    return `Mount target: ${config.config_mount_path}`;
  }

  private getFileExtension(path: string | undefined | null): string | null {
    if (!path) {
      return null;
    }
    const dotIndex = path.lastIndexOf('.');
    if (dotIndex < 0) {
      return null;
    }
    return path.slice(dotIndex).toLowerCase();
  }

  private extensionsAreCompatible(expected: string | null | undefined, actual: string | null | undefined): boolean {
    if (!expected || !actual) {
      return true;
    }
    const aliases: Record<string, string[]> = {
      '.yaml': ['.yaml', '.yml'],
      '.yml': ['.yaml', '.yml'],
    };
    return (aliases[expected] || [expected]).includes(actual);
  }

  private validateCidsRuntimeConfigs(): string | null {
    for (const config of this.cidsConfigurations) {
      if (config.config_mount_path && !config.runtime_configuration_id) {
        return `The service ${config.service_name} requires a runtime configuration because it mounts ${config.config_mount_path}. Please select one before submitting.`;
      }

      if (!config.runtime_configuration_id) {
        continue;
      }

      const selectedRuntimeConfig = this.runtimeConfigs.find(runtimeConfig => runtimeConfig.id === config.runtime_configuration_id);
      if (!selectedRuntimeConfig) {
        return `The selected runtime configuration for ${config.service_name} could not be found.`;
      }

      if (!config.config_mount_path) {
        return `The service ${config.service_name} has no config mount label. Please set its runtime config to None.`;
      }

      const actualExtension = this.getFileExtension(selectedRuntimeConfig.file_path || selectedRuntimeConfig.name);
      if (!this.extensionsAreCompatible(config.expected_config_extension, actualExtension)) {
        return `The service ${config.service_name} expects ${config.expected_config_extension} based on ${config.config_mount_path}, but ${selectedRuntimeConfig.name} uses ${actualExtension || 'no file extension'}.`;
      }
    }

    return null;
  }

  addEnvVar(): void {
    const key = this.envVarKeyControl.value?.trim();
    const value = this.envVarValueControl.value?.trim();
    if (key && value) {
      this.cidsEnvVars.push({ key, value });
      this.envVarKeyControl.reset();
      this.envVarValueControl.reset();
    }
  }

  removeEnvVar(index: number): void {
    this.cidsEnvVars.splice(index, 1);
  }

  updateEnvVarValue(index: number, event: Event): void {
    this.cidsEnvVars[index].value = (event.target as HTMLInputElement).value;
  }

  getDefaultHostId(): number | null {
    // Prefer the "Core" host
    const coreHost = this.hostSystems.find(h =>
      h.name.toLowerCase().includes('core') && h.status !== hostStatus.unavailable
    );
    if (coreHost) return coreHost.id;

    // Fall back to the host selected in the main form
    const selectedHost = this.idsForm.controls.host.value;
    if (selectedHost) return parseInt(selectedHost);

    // Fall back to the first available host
    const firstAvailable = this.hostSystems.find(h => h.status !== hostStatus.unavailable);
    return firstAvailable ? firstAvailable.id : null;
  }

  onSubmit(): void {
    // 1. Base form validation
    if (!this.idsForm.valid) {
      this.errorPopup.showError('Please fill out all required fields.', 400);
      return;
    }

    // 2. CIDS-specific validation
    if (this.deploymentType === 'DOCKER_COMPOSE') {
      // All mandatory env vars must have values
      const emptyVars = this.cidsEnvVars.filter(ev => !ev.value || ev.value.trim() === '');
      if (emptyVars.length > 0) {
        const missing = emptyVars.map(ev => ev.key).join(', ');
        this.errorPopup.showError(`Please fill in all required environment variables: ${missing}`, 400);
        return;
      }

      const runtimeConfigError = this.validateCidsRuntimeConfigs();
      if (runtimeConfigError) {
        this.errorPopup.showError(runtimeConfigError, 400);
        return;
      }
    }

    // All validation passed, build and send request
    let containerData: ContainerSetupData = {
      host_system_id: parseInt(this.idsForm.value.host!),
      ids_tool_id: parseInt(this.idsForm.value.idsTool!),
      configuration_id: parseInt(this.idsForm.value.config!),
      description: this.idsForm.value.description!,
      ruleset_id: this.idsForm.value.ruleset ? parseInt(this.idsForm.value.ruleset) : undefined,
      cids_configurations: this.cidsConfigurations.map(config => ({
        service_name: config.service_name,
        host_system_id: config.host_system_id,
        count: config.count,
        runtime_configuration_id: config.config_mount_path
          ? (config.runtime_configuration_id ?? undefined)
          : undefined,
      })),
      env_vars: this.deploymentType === 'DOCKER_COMPOSE' && this.cidsEnvVars.length > 0
        ? this.cidsEnvVars.reduce((acc, ev) => ({ ...acc, [ev.key]: ev.value }), {} as { [key: string]: string })
        : undefined
    };

    this.idsService.sendContainerSetupData(containerData)
      .subscribe(_res => {
          this.router.navigate(["/"]);
        },
        err => {
          this.errorPopup.showError(err.error["error"], err.status);
        });
  }

  onEnsembleSubmit() {
    if (this.ensembleForm.valid) {
      let ensembleData: EnsembleSetupData = {
        name: this.ensembleForm.value.name!,
        description: this.ensembleForm.value.description!,
        technique: parseInt(this.ensembleForm.value.technique!),
        container_ids: this.ensembleForm.value.containers!
      }
      this.ensembleService.sendEnsembleData(ensembleData)
        .subscribe(_res => {
          this.router.navigate(["/"])
        },
          err => {
            this.errorPopup.showError(err.error["error"], err.status);
          })
    }

  }

  getConfigurations() {
    let type: string = fileTypes.configuration;
    this.configService.getAllConfigurationsByType(type)
      .subscribe(data => {
        const allConfigs = data.map(config => ({
          id: config.id, name: config.name, file_path: config.file_path, description: config.description, file_type: config.file_type, config_type: config.config_type
        }));

        // Filter for specific config types
        this.runtimeConfigs = allConfigs.filter(c => c.config_type === 'RUNTIME' || !c.config_type || c.config_type === 'CONFIGURATION');
        this.deploymentConfigs = allConfigs.filter(c => c.config_type === 'DEPLOYMENT');

        // Default: show all until a tool is selected
        this.filteredConfigs = allConfigs;
      });
  }

  getRuleSets() {
    let type: string = fileTypes.ruleSet;
    this.configService.getAllConfigurationsByType(type)
      .subscribe(data => {
        this.ruleSets = data.map(config => ({
          id: config.id, name: config.name, file_path: config.file_path, description: config.description, file_type: config.file_type
        }));
      });
  }

  getAllIdsTools() {
    this.idsService.getAllIdsTools()
      .subscribe(data => {
        this.idsTools = data.map(tool => ({
          id: tool.id,
          name: tool.name,
          ids_type: tool.ids_type,
          analysis_method: tool.analysis_method,
          requires_ruleset: tool.requires_ruleset,
          image_name: tool.image_name,
          image_tag: tool.image_tag,
          deployment_type: tool.deployment_type,
          required_env_vars: tool.required_env_vars || ''
        }));
      });
  }

  getAllContainer() {
    this.idsService.getAllNonEnsembledIdsContainer()
      .subscribe(data => {
        this.containers = data.map(container => ({
          id: container.id,
          name: container.name,
          host_system_id: container.host_system_id,
          port: container.port,
          status: container.status,
          configuration_id: container.configuration_id,
          ids_tool_id: container.ids_tool_id,
          description: container.description,
          ruleset_id: container.ruleset_id,
          type: container.type
        }))
      })
  }


  getAllTechniques() {
    this.ensembleService.getAllTechnqiues()
      .subscribe(data => {
        this.ensembleTechniques = data.map(technique => ({
          id: technique.id,
          name: technique.name,
          description: technique.description,
          function_name: technique.function_name
        }));
      });
  }

  setUserChoice(choice: string) {
    this.userChoice = choice;
  }

  getAllHostSystems() {
    this.hostService.getAllHosts().subscribe(hosts => {
      this.hostSystems = hosts.map(hostSystem => ({
        id: hostSystem.id,
        name: hostSystem.name,
        host: hostSystem.host,
        docker_port: hostSystem.docker_port,
        status: hostSystem.status
      }));
    })
  }

}
