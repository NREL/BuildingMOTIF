import { Component, OnInit } from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import { ModelNewService } from './model-new.service';
import {Router} from "@angular/router"
import { Model } from '../types';

@Component({
  selector: 'app-model-new',
  templateUrl: './model-new.component.html',
  styleUrls: ['./model-new.component.css'],
  providers: [ModelNewService]
})
export class ModelNewComponent {
  newModelForm = new FormGroup({
    nameControl: new FormControl("", Validators.required),
    descriptionControl: new FormControl(""),
  })
  

  constructor(private router: Router, private modelNewService: ModelNewService) { }

  createModel = () => {
    const name = this.newModelForm.value.nameControl
    const description = this.newModelForm.value.descriptionControl

    this.modelNewService.createModel(name, description).subscribe({
      next: (newModel: Model) => {
        this.router.navigate([`/models/${newModel.id}`])
      }, // success path
      error: (error) => {console.log(error)}, // error path  
    })
  }
}
