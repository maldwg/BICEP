import { Component, Inject, OnInit, ViewChild } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogActions, MatDialogContent, MatDialogRef, MatDialogTitle } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { AlertComponent } from '../../components/alert-component/alert-component.component';
import { Configuration, ConfigurationUpdateData } from '../../models/configuration';
import { ConfigService } from '../../services/config/config.service';

@Component({
    selector: 'app-config-details',
    imports: [
      AlertComponent,
      ReactiveFormsModule,
      MatButtonModule,
      MatDialogActions,
      MatDialogContent,
      MatDialogTitle,
      MatFormFieldModule,
      MatIconModule,
      MatInputModule
    ],
    templateUrl: './config-details.component.html',
    styleUrl: './config-details.component.scss'
})
export class ConfigDetailsComponent implements OnInit {
  @ViewChild(AlertComponent) errorPopup!: AlertComponent;

  loading = true;
  saving = false;
  closing = false;

  configForm = new FormGroup({
    name: new FormControl('', Validators.required),
    description: new FormControl(''),
    fileContent: new FormControl('', Validators.required),
  });

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: { configuration: Configuration },
    private configService: ConfigService,
    private dialogRef: MatDialogRef<ConfigDetailsComponent>
  ) { }

  ngOnInit(): void {
    this.configService.getDeserializedConfiguration(this.data.configuration.id)
      .subscribe({
        next: configuration => {
          this.configForm.patchValue({
            name: configuration.name,
            description: configuration.description,
            fileContent: configuration.file_content
          });
          this.loading = false;
        },
        error: err => {
          this.loading = false;
          this.errorPopup.showError(err.error?.error || 'Could not load configuration content.', err.status || 500);
        }
      });
  }

  save(): void {
    if (this.configForm.invalid) {
      this.errorPopup.showError('Name and file content are required.', 400);
      return;
    }

    const payload: ConfigurationUpdateData = {
      id: this.data.configuration.id,
      name: this.configForm.value.name!,
      description: this.configForm.value.description || '',
      file_content: this.configForm.value.fileContent!
    };

    this.saving = true;
    this.configService.updateConfiguration(payload)
      .subscribe({
        next: configuration => {
          this.saving = false;
          this.closeWithLoading(configuration);
        },
        error: err => {
          this.saving = false;
          this.errorPopup.showError(err.error?.error || 'Could not save configuration.', err.status || 500);
        }
      });
  }

  exit(): void {
    this.closeWithLoading();
  }

  private closeWithLoading(result?: unknown): void {
    this.closing = true;
    this.configForm.controls.fileContent.setValue('', { emitEvent: false });
    setTimeout(() => this.dialogRef.close(result), 80);
  }
}
