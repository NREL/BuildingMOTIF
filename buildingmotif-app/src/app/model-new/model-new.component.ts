import { Component, OnInit } from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import { ModelNewService } from './model-new.service';
import {Router} from "@angular/router"
import { Model } from '../types';
import {MatSnackBar} from '@angular/material/snack-bar';

@Component({
  selector: 'app-model-new',
  templateUrl: './model-new.component.html',
  styleUrls: ['./model-new.component.css'],
  providers: [ModelNewService]
})
export class ModelNewComponent {
  newModelForm = new FormGroup({
    nameControl: new FormControl("", [Validators.required, noInValidCharacatersValidator]),
    descriptionControl: new FormControl(""),
  })
  

  constructor(private router: Router, private modelNewService: ModelNewService, private _snackBar: MatSnackBar) { }

  createModel = () => {
    const name = this.newModelForm.value.nameControl
    const description = this.newModelForm.value.descriptionControl

    this.modelNewService.createModel(name, description).subscribe({
      next: (newModel: Model) => {
        this.router.navigate([`/models/${newModel.id}`])
      }, // success path
      error: (error) => {
        this._snackBar.open( error, "close", {
          duration: 3000,
        });
      }, // error path
    })
  }
}


function noInValidCharacatersValidator(control: FormControl) {
  const invalidCharacter = '<>" {}|\\^`';

  for (const c of control?.value.split("")) {
    if(invalidCharacter.includes(c)){
      return {
        invalidCharacter: "contains invalid characater: " + c
      }
    }
  }

  return null;
}
