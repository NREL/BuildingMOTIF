import { Component, Input } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Library } from '../library/library.service'
import { FormControl, Validators, FormGroup, ValidatorFn, ValidationErrors, AbstractControl } from '@angular/forms';
import { ModelValidateService } from './model-validate.service';

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
  libraries: Library[] = [];
  selectedLibrariesForm: FormGroup = new FormGroup({});
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
    this.libraries = this.route.snapshot.data["ModelValidateResolver"]

    const selectedLibaryControls: { [id: number]: FormControl } = this.libraries.reduce((acc, curr) => {
      return { ...acc, [curr.id]: new FormControl(false) }
    }, {});
    this.selectedLibrariesForm = new FormGroup(selectedLibaryControls, {validators: NoneSelectedValidator()})
  }

  validate(): void {
    const selectedLibraryIds = Object.entries(this.selectedLibrariesForm.value)
      .filter(([id, selected]) => selected)
      .map(([id, selected]) => id);

    if (!!this.modelId){
      this.showValidatingSpinner = true;

      this.modelValidateService.validateModel(this.modelId, selectedLibraryIds).subscribe(
        res => {this.validationResponse = res},
        err => {},
        () => {this.showValidatingSpinner = false},
      );
    }
  }
}
