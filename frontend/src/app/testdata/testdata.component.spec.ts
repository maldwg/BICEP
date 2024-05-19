import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TestdataComponent } from './testdata.component';

describe('TestdataComponent', () => {
  let component: TestdataComponent;
  let fixture: ComponentFixture<TestdataComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TestdataComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(TestdataComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
