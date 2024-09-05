import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HostCreationComponent } from './host-creation.component';

describe('HostCreationComponent', () => {
  let component: HostCreationComponent;
  let fixture: ComponentFixture<HostCreationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostCreationComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(HostCreationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
