import { Component, Input, OnInit} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormControl, FormGroup, ValidatorFn, ValidationErrors, AbstractControl } from '@angular/forms';
import { ModelValidateService, ValidationResponse } from './model-validate.service';
import { LibraryService, Library } from '../library/library.service';

// verify that at least one checkbox is checked in the FormGroup
function NoneSelectedValidator(): ValidatorFn {
    return (control: AbstractControl) => {
        const formGroup = control as FormGroup;
        const checkedKeys = Object.keys(formGroup.controls).filter((key) => formGroup.controls[key].value);

        if (checkedKeys.length === 0) { return { noneSelected: {value: true}}; }

        return null;
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
  libraries?: Library[] = undefined;
  selectedLibrariesForm: FormGroup = new FormGroup({});
  validationResponse?: ValidationResponse = undefined;
  showGettingLibrariesSpinner = false;
  showValidatingSpinner = false;

  codeMirrorOptions: any = {
    theme: 'material',
    mode: 'text',
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
    this.showGettingLibrariesSpinner = true;
    this.libraryService.getAllLibraries().subscribe(
      res => {
        this.populateSelectedLibrariesControls(res);
        this.libraries = res;
      },
      err => {},
      () => {this.showGettingLibrariesSpinner = false},
    );
  }

  populateSelectedLibrariesControls(libraries: Library[]): void {
    const selectedLibrariesControls: { [library_index: number]: FormControl } = libraries.reduce((acc, _, i) => {
      return { ...acc, [i]: new FormControl(false) }
    }, {});
    this.selectedLibrariesForm = new FormGroup(selectedLibrariesControls, {validators: NoneSelectedValidator()})
  }

  validate(): void {
    if (this.libraries == undefined) return;

    const selectedLibraries = this.libraries.filter((_, i) => this.selectedLibrariesForm.value[i])
    const args = selectedLibraries.map(l => l.id);

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
