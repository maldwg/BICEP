import { Routes } from '@angular/router';

export const routes: Routes = [
    { path: "", loadComponent: () => import("./dashboard/dashboard.component").then(mod => mod.DashboardComponent) },
    { path: "upload", loadComponent: () => import("./config/config.component").then(mod => mod.ConfigComponent) },
    { path: "setup", loadComponent: () => import("./setup/setup.component").then(mod => mod.SetupComponent) },
    { path: "metrics", loadComponent: () => import("./metrics/metrics.component").then(mod => mod.MetricsComponent) },
    { path: "hosts", loadComponent: () => import("./docker-hosts/docker-hosts.component").then(mod => mod.DockerHostsComponent) },
    { path: "benchmarking/start", loadComponent: () => import("./benchmarking/start/start.component").then(mod => mod.StartComponent) },
    { path: "benchmarking/results", loadComponent: () => import("./benchmarking/results/results.component").then(mod => mod.ResultsComponent) },
    { path: "monitoring", loadComponent: () => import("./monitoring/monitoring.component").then(mod => mod.MonitoringComponent) },
    { path: "ids-tools", loadComponent: () => import("./ids-tools/ids-tools.component").then(mod => mod.IdsToolsComponent) }
];
