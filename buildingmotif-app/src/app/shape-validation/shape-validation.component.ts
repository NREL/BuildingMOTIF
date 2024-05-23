import { Component, OnInit, Input} from '@angular/core';
import { LibraryService, Shape } from '../library/library.service';
import { ModelDetailService } from '../model-detail/model-detail.service';
import {ShapeValidationService} from './shape-validate.service';
import { ValidationResponse } from '../model-validate/model-validate.service';
import { FormControl, FormGroup, Validators, ValidationErrors, ValidatorFn, AbstractControl } from '@angular/forms';


export function forbiddenNameValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    let value = control.value as Set<Shape>;
    const forbidden = value.size <= 0;
    return forbidden ? {empty: {value: control.value}} : null;
  };
}

@Component({
  selector: 'app-shape-validation',
  templateUrl: './shape-validation.component.html',
  providers: [LibraryService, ModelDetailService, ShapeValidationService],
  styleUrls: ['./shape-validation.component.css']
})
export class ShapeValidationComponent implements OnInit {
  @Input() modelId: number | undefined;
  showGettingShapesSpinner = false;
  showValidatingSpinner = false;
  shapes?:  {[definition_type: string]: Shape[]} = undefined;
  targetNodes?: string[] = undefined;
  formGroup = new FormGroup({
    shapes: new FormControl(new Set(), forbiddenNameValidator()),
    targetNode: new FormControl(null, Validators.required)
  });
  response?: Record<string, string[]> = undefined;



  constructor(private libraryService: LibraryService, private modelDetailService: ModelDetailService, private shapeValidationService: ShapeValidationService) {}

  ngOnInit(): void {
    this.showGettingShapesSpinner = true;
    this.libraryService.getAllShapes().subscribe(
      res => {
        this.shapes = res;
      },
      err => {},
      () => {this.showGettingShapesSpinner = false},
    );

    if (this.modelId === undefined) return;
    this.modelDetailService.getTargetNodes(this.modelId).subscribe(
      res => {
        this.targetNodes = res;
      },
      err => {},
    );
  }


  toggle_selected(shape: Shape): void {
    var selectedShapes = this.formGroup.controls['shapes'].value
    if (selectedShapes === null) return;

    if(selectedShapes.has(shape)){
      selectedShapes.delete(shape)
    } else {
      selectedShapes.add(shape)
    }

    this.formGroup.controls['shapes'].setValue(selectedShapes)
    this.formGroup.controls['shapes'].markAsTouched()
    this.formGroup.controls['shapes'].markAsDirty()
  }

  validate(){
    var selected_shapes = this.formGroup.controls['shapes'].value;
    if (selected_shapes === null) return;
    const shape_collection_ids = new Set([...selected_shapes].map(s => s.shape_collection_id));
    const shape_uris =  new Set([...selected_shapes].map(s => s.shape_uri));

    var target_class = this.formGroup.controls['targetNode'].value

    if (this.modelId === undefined) return;
    if (target_class === null) return;

    this.showValidatingSpinner = true;
    this.shapeValidationService.validateModelShape(this.modelId, [...shape_collection_ids], [...shape_uris], target_class[0]).subscribe(
      res => {
        this.response = res;
        console.log(this.response)
      },
      err => {},
      () => {this.showValidatingSpinner = false}
    );
  }
}
