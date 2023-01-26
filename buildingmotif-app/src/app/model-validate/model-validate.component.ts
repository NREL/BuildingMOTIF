import { Component, Input } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Library } from '../library/library.service'
import { FormControl, Validators, FormGroup, ValidatorFn, ValidationErrors, AbstractControl } from '@angular/forms';
import { ModelValidateService } from './model-validate.service';

export interface Shape {
  library_name: string;
  library_id: number;
  uri: string;
  label: string;
  description: string;
}

function NoneSelectedValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const anyIsTrue = Object.values(control.value).some(v => v)
    return anyIsTrue ? null: {noneSelected: {value: true}};
  };
}

@Component({
  selector: 'app-model-validate',
  templateUrl: './model-validate.component.html',
  providers: [ModelValidateService],
  styleUrls: ['./model-validate.component.css'],
})
export class ModelValidateComponent {
  @Input() modelId: number | undefined;
  shapes: Shape[] = [];
  selectedShapesForm: FormGroup = new FormGroup({});
  validationResponse = "";
  showValidatingSpinner = false;

  codeMirrorOptions: any = {
    theme: 'material',
    mode: 'application/json',
    lineNumbers: true,
    lineWrapping: true,
    foldGutter: true,
    gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter', 'CodeMirror-lint-markers'],
    autoCloseBrackets: true,
    matchBrackets: true,
    lint: true,
    readOnly: true,
  };

  constructor(private route: ActivatedRoute, private modelValidateService: ModelValidateService) {
    this.shapes = this.route.snapshot.data["ModelValidateResolver"]

    const selectedShapesControls: { [shape_uri: string]: FormControl } = this.shapes.reduce((acc, curr) => {
      return { ...acc, [curr.uri]: new FormControl(false) }
    }, {});
    console.log(selectedShapesControls)
    this.selectedShapesForm = new FormGroup(selectedShapesControls, {validators: NoneSelectedValidator()})
  }

  validate(): void {
    const selectedShapeIds = Object.entries(this.selectedShapesForm.value)
      .filter(([id, selected]) => selected)
      .map(([id, selected]) => id);

    if (!!this.modelId){
      this.showValidatingSpinner = true;

      this.modelValidateService.validateModel(this.modelId, selectedShapeIds).subscribe(
        res => {this.validationResponse = res},
        err => {},
        () => {this.showValidatingSpinner = false},
      );
    }
  }
}
