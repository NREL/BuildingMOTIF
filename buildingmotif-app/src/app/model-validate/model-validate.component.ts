import { Component, Input, OnInit} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormControl, FormGroup, ValidatorFn, ValidationErrors, AbstractControl } from '@angular/forms';
import { ModelValidateService } from './model-validate.service';
import { LibraryService, Shape } from '../library/library.service';

function NoneSelectedValidator(): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const anyIsTrue = Object.values(control.value).some(v => v)
    return anyIsTrue ? null: {noneSelected: {value: true}};
  };
}

@Component({
  selector: 'app-model-validate',
  templateUrl: './model-validate.component.html',
  providers: [ModelValidateService, LibraryService],
  styleUrls: ['./model-validate.component.css'],
})
export class ModelValidateComponent implements OnInit{
  @Input() modelId: number | undefined;
  shapes?: Shape[] = undefined;
  selectedShapesForm: FormGroup = new FormGroup({});
  validationResponse = "";
  showGettingShapesSpinner = false;
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

  constructor(private modelValidateService: ModelValidateService, private libraryService: LibraryService) {}

  ngOnInit(): void {
    this.showGettingShapesSpinner = true;
    this.libraryService.getAllShapes().subscribe(
      res => {this.shapes = res},
      err => {},
      () => {this.showGettingShapesSpinner = false},
    );

    if (this.shapes == undefined) return;

    const selectedShapesControls: { [shape_index: number]: FormControl } = this.shapes.reduce((acc, _, i) => {
      return { ...acc, [i]: new FormControl(false) }
    }, {});
    this.selectedShapesForm = new FormGroup(selectedShapesControls, {validators: NoneSelectedValidator()})
  }

  validate(): void {
    if (this.shapes == undefined) return;

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
