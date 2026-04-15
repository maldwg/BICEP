import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { MatDialog } from '@angular/material/dialog';

import { DockerHostsComponent } from './docker-hosts.component';
import { DockerHostService } from '../services/host/host.service';

describe('DockerHostsComponent', () => {
  let component: DockerHostsComponent;
  let fixture: ComponentFixture<DockerHostsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DockerHostsComponent],
      providers: [
        {
          provide: DockerHostService,
          useValue: {
            getAllHosts: () => of([]),
            addHost: () => of(null),
            removeHost: () => of(null),
          },
        },
        {
          provide: MatDialog,
          useValue: {
            open: () => ({
              afterClosed: () => of(null),
            }),
          },
        },
      ],
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(DockerHostsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
