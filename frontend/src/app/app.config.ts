import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { provideRouter } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { provideEchartsCore } from 'ngx-echarts';
import * as echarts from 'echarts/core';
import { routes } from './app.routes';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import {} from '@angular/common/http';

import { BarChart, LineChart, RadarChart, BoxplotChart } from 'echarts/charts';

// Import the components you need:
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DatasetComponent,
  LegendComponent,
} from 'echarts/components';

// Import renderer:
import { CanvasRenderer } from 'echarts/renderers';

// Register everything with ECharts:
echarts.use([
  BarChart,
  LineChart,
  RadarChart,
  BoxplotChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DatasetComponent,
  LegendComponent,
  CanvasRenderer
]);

export const appConfig: ApplicationConfig = {
  providers: [provideEchartsCore({ echarts }), provideRouter(routes), provideAnimationsAsync(), provideAnimationsAsync(),importProvidersFrom(HttpClientModule)]
};
