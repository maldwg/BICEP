import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IdsEditComponent } from './ids-edit.component';

describe('IdsEditComponent', () => {
  let component: IdsEditComponent;
  let fixture: ComponentFixture<IdsEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IdsEditComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(IdsEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
