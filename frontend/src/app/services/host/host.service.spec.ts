import { TestBed } from '@angular/core/testing';

import { DockerHostService } from './host.service';

describe('DockerHostService', () => {
  let service: DockerHostService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(DockerHostService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
