import { Component,  OnInit } from '@angular/core';
import { environment } from '../../environments/environment';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
    selector: 'app-metrics',
    imports: [],
    templateUrl: './metrics.component.html',
    styleUrl: './metrics.component.css'
})
export class MetricsComponent implements OnInit {

  grafanaDashboardUrl: SafeResourceUrl = "";

  constructor(private sanitizer: DomSanitizer){}

  ngOnInit(): void {
    const unsafeUrl = environment.grafanaUrl + "/d/edv2tl6dk6gaod/bicep?orgId=1";
    this.grafanaDashboardUrl = this.sanitizer.bypassSecurityTrustResourceUrl(unsafeUrl);
  }
}
