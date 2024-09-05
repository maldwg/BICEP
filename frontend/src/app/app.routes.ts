import { Routes } from '@angular/router';

export const routes: Routes = [
    {path: "", loadComponent: () => import("./dashboard/dashboard.component").then(mod => mod.DashboardComponent)},
    {path: "upload", loadComponent: () => import("./config/config.component").then(mod => mod.ConfigComponent)},
    {path: "setup", loadComponent: () => import("./setup/setup.component").then(mod => mod.SetupComponent)},
    {path: "metrics", loadComponent: () => import("./metrics/metrics.component").then(mod => mod.MetricsComponent)},
    {path: "hosts", loadComponent: () => import("./hosts/hosts.component").then(mod => mod.HostsComponent)}

];
