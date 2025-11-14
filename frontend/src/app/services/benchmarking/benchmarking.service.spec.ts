import { TestBed } from '@angular/core/testing';

import { BenchmarkingService } from './benchmarking.service';

describe('BenchmarkingService', () => {
  let service: BenchmarkingService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(BenchmarkingService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
