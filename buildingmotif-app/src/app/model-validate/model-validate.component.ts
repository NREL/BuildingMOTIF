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

    const selectedShapesControls: { [shape_index: number]: FormControl } = this.shapes.reduce((acc, _, i) => {
      return { ...acc, [i]: new FormControl(false) }
    }, {});
    this.selectedShapesForm = new FormGroup(selectedShapesControls, {validators: NoneSelectedValidator()})
  }

  validate(): void {
    const selectedShapes = this.shapes.filter((_, i) => this.selectedShapesForm.value[i])
    const args = selectedShapes.map(s => {return {library_id: s.library_id, shape_uri: s.uri}})

    if (!!this.modelId){
      this.showValidatingSpinner = true;

      this.modelValidateService.validateModel(this.modelId, args).subscribe(
        res => {this.validationResponse = res},
        err => {},
        () => {this.showValidatingSpinner = false},
      );
    }
  }
}
