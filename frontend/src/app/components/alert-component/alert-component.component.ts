import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-alert-component',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './alert-component.component.html',
  styleUrl: './alert-component.component.css'
})
export class AlertComponent {
  visible = false;
  message = '';

  showError(msg: string) {
    this.message = msg;
    this.visible = true;

    // Auto-hide after 5 seconds
    setTimeout(() => this.visible = false, 5000);
  }

  closePopup() {
    this.visible = false;
  }

}
