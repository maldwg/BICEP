import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ConfigCreationComponent } from './config-creation.component';

describe('ConfigCreationComponent', () => {
  let component: ConfigCreationComponent;
  let fixture: ComponentFixture<ConfigCreationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfigCreationComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(ConfigCreationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
