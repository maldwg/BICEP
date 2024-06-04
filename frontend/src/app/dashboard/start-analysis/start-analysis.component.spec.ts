import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StartAnalysisComponent } from './start-analysis.component';

describe('StartAnalysisComponent', () => {
  let component: StartAnalysisComponent;
  let fixture: ComponentFixture<StartAnalysisComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StartAnalysisComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(StartAnalysisComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
