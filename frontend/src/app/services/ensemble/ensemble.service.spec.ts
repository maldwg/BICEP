import { TestBed } from '@angular/core/testing';

import { EnsembleService } from './ensemble.service';

describe('EnsembleService', () => {
  let service: EnsembleService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(EnsembleService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
