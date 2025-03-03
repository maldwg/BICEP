import { Component } from '@angular/core';
import { environment } from '../../environments/environment';
@Component({
  selector: 'app-metrics',
  standalone: true,
  imports: [],
  templateUrl: './metrics.component.html',
  styleUrl: './metrics.component.css'
})
export class MetricsComponent {


  grafanaDashboardUrl = environment.grafanaUrl + "/d/edv2tl6dk6gaod/bicep?orgId=1";

}
