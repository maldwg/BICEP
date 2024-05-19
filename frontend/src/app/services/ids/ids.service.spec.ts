import { TestBed } from '@angular/core/testing';

import { IdsService } from './ids.service';

describe('IdsService', () => {
  let service: IdsService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(IdsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
