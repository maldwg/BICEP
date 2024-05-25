import { Routes } from '@angular/router';

export const routes: Routes = [
    {path: "", loadComponent: () => import("./dashboard/dashboard.component").then(mod => mod.DashboardComponent)},
    {path: "config", loadComponent: () => import("./config/config.component").then(mod => mod.ConfigComponent)},
    {path: "setup", loadComponent: () => import("./setup/setup.component").then(mod => mod.SetupComponent)},

];
