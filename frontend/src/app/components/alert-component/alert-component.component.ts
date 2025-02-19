import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import {MatIconModule} from '@angular/material/icon';

@Component({
  selector: 'app-alert-component',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './alert-component.component.html',
  styleUrl: './alert-component.component.css'
})
export class AlertComponent {
  errors: { id: number, message: string }[] = [];

  showError(msg: string) {
    const id = Date.now(); // Unique ID for tracking
    this.errors.push({ id, message: msg });

    // Auto-remove after 5 seconds
    setTimeout(() => this.removeErrorById(id), 5000);
  }

  removeError(error: { id: number, message: string }) {
    this.errors = this.errors.filter(e => e.id !== error.id);
  }

  private removeErrorById(id: number) {
    this.errors = this.errors.filter(e => e.id !== id);
  }

}
