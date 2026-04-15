import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { of } from 'rxjs';

import { IdsEditComponent } from './ids-edit.component';
import { ConfigService } from '../../services/config/config.service';

describe('IdsEditComponent', () => {
  let component: IdsEditComponent;
  let fixture: ComponentFixture<IdsEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IdsEditComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            container: {
              id: 1,
              name: 'Test CIDS',
              description: 'desc',
              host_system_id: 1,
              port: 8080,
              status: 'IDLE',
              configuration_id: 10,
              ids_tool_id: 5,
              type: 'CIDS',
              components: [
                { id: 11, service_name: 'sensor', runtime_configuration_id: 2, count: 1 },
                { id: 12, service_name: 'aggregator', runtime_configuration_id: 3, count: 1 },
              ],
            },
            configList: [
              { id: 2, name: 'sensor.yaml', file_type: 'RUNTIME' },
              { id: 3, name: 'agg.yaml', file_type: 'RUNTIME' },
              { id: 10, name: 'compose.yaml', file_type: 'DEPLOYMENT' },
            ],
            idsToolList: [
              {
                id: 5,
                name: 'Compose IDS',
                analysis_method: 'NETWORK',
                ids_type: 'CIDS',
                requires_ruleset: false,
                image_name: 'ids/image',
                image_tag: 'latest',
                deployment_type: 'DOCKER_COMPOSE',
                required_env_vars: '',
              },
            ],
          },
        },
        {
          provide: MatDialogRef,
          useValue: { close: jasmine.createSpy('close') },
        },
        {
          provide: ConfigService,
          useValue: {
            getConfigurationServices: jasmine.createSpy('getConfigurationServices').and.returnValue(of([
              {
                name: 'sensor',
                is_sensor: true,
                config_mount_path: '/app/config.yaml',
                expected_config_extension: '.yaml',
              },
              {
                name: 'aggregator',
                is_sensor: false,
                config_mount_path: null,
                expected_config_extension: null,
              },
            ])),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(IdsEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should only allow runtime config editing for labeled services', () => {
    const sensor = component.data.container.components?.[0];
    const aggregator = component.data.container.components?.[1];

    expect(component.canEditRuntimeConfig(sensor)).toBeTrue();
    expect(component.canEditRuntimeConfig(aggregator)).toBeFalse();
    expect(aggregator.runtime_configuration_id).toBeNull();
  });
});
