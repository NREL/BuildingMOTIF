import { Component, Input, OnInit} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormControl, FormGroup, ValidatorFn, ValidationErrors, AbstractControl } from '@angular/forms';
import { ModelValidateService } from './model-validate.service';
import { LibraryService, Library } from '../library/library.service';

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
  libraries?: Library[] = undefined;
  selectedLibrariesForm: FormGroup = new FormGroup({});
  validationResponse = "";
  showGettingLibrariesSpinner = false;
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
    this.showGettingLibrariesSpinner = true;
    this.libraryService.getAllLibraries().subscribe(
      res => {this.libraries = res},
      err => {},
      () => {this.showGettingLibrariesSpinner = false},
    );

    if (this.libraries == undefined) return;

    const selectedLibrariesControls: { [library_index: number]: FormControl } = this.libraries.reduce((acc, _, i) => {
      return { ...acc, [i]: new FormControl(false) }
    }, {});
    this.selectedLibrariesForm = new FormGroup(selectedLibrariesControls, {validators: NoneSelectedValidator()})
  }

  validate(): void {
    if (this.libraries == undefined) return;

    const selectedLibraries = this.libraries.filter((_, i) => this.selectedLibrariesForm.value[i])
    const args = selectedLibraries.map(l => {return l.id})

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
