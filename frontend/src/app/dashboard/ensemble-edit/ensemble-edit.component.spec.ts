import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EnsembleEditComponent } from './ensemble-edit.component';

describe('EnsembleEditComponent', () => {
  let component: EnsembleEditComponent;
  let fixture: ComponentFixture<EnsembleEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnsembleEditComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(EnsembleEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
