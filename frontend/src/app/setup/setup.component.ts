import { Component, OnChanges, OnInit, ViewChild } from '@angular/core';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormControl, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { IdsService } from '../services/ids/ids.service';
import { ConfigService } from '../services/config/config.service';
import { Router } from '@angular/router';
import { Container, ContainerSetupData, CidsServiceConfig } from '../models/container';
import { Configuration } from '../models/configuration';
import { fileTypes } from '../models/acceptedFileTypes';
import { IdsTool } from '../models/ids';
import { CommonModule } from '@angular/common';
import { Ensemble, EnsembleSetupData, EnsembleTechnique } from '../models/ensemble';
import { EnsembleService } from '../services/ensemble/ensemble.service';
import { describe } from 'node:test';
import { runInThisContext } from 'node:vm';
import { MatTooltipModule } from '@angular/material/tooltip';
import { HttpResponse } from '@angular/common/http';
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
  //  TODO 5: add name to IDS creation
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

  idsConfigs: Configuration[] = [];
  ruleSets: Configuration[] = [];
  idsTools: IdsTool[] = [];
  hostSystems: DockerHostSystem[] = [];
  containers: Container[] = [];
  ensembles: Ensemble[] = [];
  ensembleTechniques: EnsembleTechnique[] = [];
  userChoice = "";
  requiresRuleset = false;

  // CIDS Support
  selectedTool: IdsTool | undefined;
  cidsConfigurations: CidsServiceConfig[] = [];
  availableServices: string[] = [];
  deploymentType = "SINGLE_CONTAINER";

  // Runtime Configs available for selection
  runtimeConfigs: Configuration[] = [];
  deploymentConfigs: Configuration[] = [];

  // Helper for CIDS Form: Host -> Services
  cidsHostSelection = new FormControl();
  cidsServiceSelection = new FormControl();
  cidsCountSelection = new FormControl(1);
  cidsRuntimeConfigSelection = new FormControl(); // For CIDS Runtime Config
  cidsComposeSelection = new FormControl(); // Select additional compose files? Or just use main config?
  // Current plan: Use main config for services parsing.



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
    this.getAllEnemsebles();
    this.getAllTechniques();
    this.getConfigurations();
    this.getRuleSets();
    this.getAllHostSystems();



    this.idsForm.controls.idsTool.valueChanges.subscribe((toolId) => {
      this.selectedTool = this.idsTools.find(tool => tool.id == parseInt(toolId!));
      this.requiresRuleset = this.selectedTool ? this.selectedTool.requires_ruleset : false;
      this.deploymentType = this.selectedTool?.deployment_type || "SINGLE_CONTAINER";

      // Reset CIDS state on tool change
      this.cidsConfigurations = [];
      this.availableServices = [];
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
              service_name: svc,
              count: 1
            }));
          }
        });
      }
    });

  }

  addCidsConfiguration() {
    if (this.cidsHostSelection.value && this.cidsServiceSelection.value) {
      const newConfig: CidsServiceConfig = {
        host_system_id: parseInt(this.cidsHostSelection.value),
        service_name: this.cidsServiceSelection.value,
        count: this.cidsCountSelection.value || 1
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

  getHostName(id: number): string {
    return this.hostSystems.find(h => h.id === id)?.name || 'Unknown';
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
    if (this.idsForm.valid) {
      let containerData: ContainerSetupData = {
        host_system_id: parseInt(this.idsForm.value.host!),
        ids_tool_id: parseInt(this.idsForm.value.idsTool!),
        configuration_id: parseInt(this.idsForm.value.config!),
        description: this.idsForm.value.description!,
        ruleset_id: this.idsForm.value.ruleset ? parseInt(this.idsForm.value.ruleset) : undefined,
        cids_configurations: this.cidsConfigurations,
        runtime_configuration_id: this.deploymentType === 'DOCKER_COMPOSE' && this.cidsRuntimeConfigSelection.value ? parseInt(this.cidsRuntimeConfigSelection.value) : undefined
      };
      this.idsService.sendContainerSetupData(containerData)
        .subscribe(res => console.log(res),
          err => {
            this.errorPopup.showError(err.error["error"], err.status);
          });
      this.router.navigate(["/"]);
    }
  }

  onEnsembleSubmit() {
    if (this.ensembleForm.valid) {
      let ensembleData: EnsembleSetupData = {
        name: this.ensembleForm.value.name!,
        description: this.ensembleForm.value.description!,
        technique: parseInt(this.ensembleForm.value.technique!),
        container_ids: this.ensembleForm.value.containers!
      }
      console.log(this.ensembleForm)
      console.log(this.ensembleForm.value.containers);
      this.ensembleService.sendEnsembleData(ensembleData)
        .subscribe(res => {
          // TODO 5: go thorugh each response object here and see if it was succesful??
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
        this.idsConfigs = allConfigs; // For backward compatibility / general list

        // Filter for specific config types
        this.runtimeConfigs = allConfigs.filter(c => c.config_type === 'RUNTIME' || !c.config_type || c.config_type === 'CONFIGURATION');
        this.deploymentConfigs = allConfigs.filter(c => c.config_type === 'DEPLOYMENT');
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
          deployment_type: tool.deployment_type
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

  getAllEnemsebles() {
    this.ensembleService.getAllEnsembles()
      .subscribe(data => {
        this.ensembles = data.map(ensemble => ({
          id: ensemble.id,
          name: ensemble.name,
          description: ensemble.description,
          technique_id: ensemble.technique_id,
          status: ensemble.status,
          current_analysis_id: ensemble.current_analysis_id
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
