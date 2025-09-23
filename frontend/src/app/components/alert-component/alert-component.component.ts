import { Component, Input } from '@angular/core';

import {MatIconModule} from '@angular/material/icon';
import {v4 as uuidv4} from 'uuid';

@Component({
    selector: 'app-alert-component',
    imports: [MatIconModule],
    templateUrl: './alert-component.component.html',
    styleUrl: './alert-component.component.css'
})
export class AlertComponent {
  errors: { id: string, message: string, statusCode: number }[] = [];

  showError(msg: string, statusCode: number) {
    const id = uuidv4();
    this.errors.push({ id, message: msg, statusCode: statusCode });

    // Auto-remove after 5 seconds
    setTimeout(() => this.removeErrorById(id), 5000);
  }

  removeError(error: { id: string, message: string, statusCode: number }) {
    this.errors = this.errors.filter(e => e.id !== error.id);
  }

  private removeErrorById(id: string) {
    this.errors = this.errors.filter(e => e.id !== id);
  }

}
