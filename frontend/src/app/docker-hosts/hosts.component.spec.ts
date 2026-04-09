import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DockerHostsComponent } from './docker-hosts.component';

describe('DockerHostsComponent', () => {
  let component: DockerHostsComponent;
  let fixture: ComponentFixture<DockerHostsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DockerHostsComponent]
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
