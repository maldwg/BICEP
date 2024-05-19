import { Component, OnInit } from '@angular/core';
import {MatSelectModule} from '@angular/material/select';
import {MatInputModule} from '@angular/material/input';
import {MatFormFieldModule} from '@angular/material/form-field';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import {MatCardModule} from '@angular/material/card';
import {MatButtonModule} from '@angular/material/button';
import { IdsService } from '../services/ids/ids.service';
import { ConfigService } from '../services/config/config.service';

@Component({
  selector: 'app-setup',
  standalone: true,
  imports: [MatFormFieldModule, MatInputModule, MatSelectModule, ReactiveFormsModule, MatCardModule, FormsModule, MatButtonModule],
  templateUrl: './setup.component.html',
  styleUrl: './setup.component.css'
})
export class SetupComponent implements OnInit {
  urlControl = "localhost";
  descriptionControl = new FormControl("");
  configControl = new FormControl("");
  idsControl = new FormControl("");

  constructor(
    private idsService: IdsService,
    private configService: ConfigService,
  ) {}

  ngOnInit(): void {
    // TODO: define data types for IDS, config and testdata
    // TODO: populate services with mock data for now
    // TODO: different forms in 1 big form and submit only if all entered
    // TODO: after submit, redirect to dashboard
  }

  submitIdsData(): void {
    console.log(this.descriptionControl.value)
  }

}
