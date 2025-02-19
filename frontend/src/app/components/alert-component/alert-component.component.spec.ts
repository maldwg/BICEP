import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlertComponentComponent } from './alert-component.component';

describe('AlertComponentComponent', () => {
  let component: AlertComponentComponent;
  let fixture: ComponentFixture<AlertComponentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlertComponentComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(AlertComponentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
