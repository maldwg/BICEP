import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BenchmarkingComponent } from './benchmarking.component';

describe('BenchmarkingComponent', () => {
  let component: BenchmarkingComponent;
  let fixture: ComponentFixture<BenchmarkingComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BenchmarkingComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BenchmarkingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
