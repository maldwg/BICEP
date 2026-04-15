import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';

import { DashboardComponent } from './dashboard.component';
import { IdsService } from '../services/ids/ids.service';
import { EnsembleService } from '../services/ensemble/ensemble.service';
import { ConfigService } from '../services/config/config.service';
import { DatasetService } from '../services/dataset/dataset.service';
import { DockerHostService } from '../services/host/host.service';
import { Container } from '../models/container';
import { statusTypes } from '../models/status';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let idsServiceSpy: jasmine.SpyObj<IdsService>;

  beforeEach(async () => {
    idsServiceSpy = jasmine.createSpyObj<IdsService>('IdsService', [
      'getAllIdsContainer',
      'getAllIdsTools',
      'start_static_analysis',
      'start_network_analysis',
      'stop_analysis',
      'updateContainer',
      'removeContainerById',
    ]);

    const ensembleServiceSpy = jasmine.createSpyObj<EnsembleService>('EnsembleService', [
      'getAllEnsembles',
      'getAllTechnqiues',
      'getEnsembleContainers',
      'removeEnsemble',
      'start_static_analysis',
      'start_network_analysis',
      'stop_analysis',
      'updateEnsemble',
    ]);

    const configServiceSpy = jasmine.createSpyObj<ConfigService>('ConfigService', [
      'getAllConfigurations',
    ]);

    const datasetServiceSpy = jasmine.createSpyObj<DatasetService>('DatasetService', [
      'getAllDatasets',
    ]);

    const hostServiceSpy = jasmine.createSpyObj<DockerHostService>('DockerHostService', [
      'getAllHosts',
    ]);

    const dialogSpy = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);

    idsServiceSpy.getAllIdsContainer.and.returnValue(of([]));
    idsServiceSpy.getAllIdsTools.and.returnValue(of([]));
    ensembleServiceSpy.getAllEnsembles.and.returnValue(of([]));
    ensembleServiceSpy.getAllTechnqiues.and.returnValue(of([]));
    ensembleServiceSpy.getEnsembleContainers.and.returnValue(of([]));
    configServiceSpy.getAllConfigurations.and.returnValue(of([]));
    datasetServiceSpy.getAllDatasets.and.returnValue(of([]));
    hostServiceSpy.getAllHosts.and.returnValue(of([]));

    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        { provide: IdsService, useValue: idsServiceSpy },
        { provide: EnsembleService, useValue: ensembleServiceSpy },
        { provide: ConfigService, useValue: configServiceSpy },
        { provide: DatasetService, useValue: datasetServiceSpy },
        { provide: DockerHostService, useValue: hostServiceSpy },
        { provide: MatDialog, useValue: dialogSpy },
      ],
    }).compileComponents();

    component = TestBed.createComponent(DashboardComponent).componentInstance;
    component.errorPopup = jasmine.createSpyObj('AlertComponent', ['showError']);
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should not allow deleting a container that is still setting up', () => {
    const container: Container = {
      id: 1,
      name: 'Test IDS',
      host_system_id: 1,
      port: 8080,
      status: statusTypes.setting_up,
      description: 'desc',
      configuration_id: 1,
      ids_tool_id: 1,
      type: 'NIDS',
    };

    expect(component.containerCanBeDeleted(container)).toBeFalse();
  });

  it('should refuse delete requests for setting-up containers before calling the API', () => {
    const container: Container = {
      id: 1,
      name: 'Test IDS',
      host_system_id: 1,
      port: 8080,
      status: statusTypes.setting_up,
      description: 'desc',
      configuration_id: 1,
      ids_tool_id: 1,
      type: 'NIDS',
    };

    component.remove(container);

    expect(idsServiceSpy.removeContainerById).not.toHaveBeenCalled();
    expect(component.errorPopup.showError).toHaveBeenCalledWith(
      'An IDS that is still setting up cannot be deleted yet.',
      409
    );
  });
});
