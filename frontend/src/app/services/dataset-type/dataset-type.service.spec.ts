import { TestBed } from '@angular/core/testing';

import { DatasetTypesService } from './dataset-type.service';

describe('DatasetTypesService', () => {
  let service: DatasetTypesService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(DatasetTypesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
