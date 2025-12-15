import { Component } from '@angular/core';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatIconModule} from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import {MatMenuModule} from '@angular/material/menu';
@Component({
    selector: 'app-navbar',
    imports: [
        MatToolbarModule,
        MatIconModule,
        RouterModule,
        MatMenuModule,
    ],
    templateUrl: './navbar.component.html',
    styleUrl: './navbar.component.scss'
})
export class NavbarComponent {

}
