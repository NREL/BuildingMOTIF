import { Component, Input } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Library } from '../library/library.service';
import { FormControl, Validators } from '@angular/forms';
import { ModelValidateService } from './model-validate.service'

@Component({
  selector: 'app-model-validate',
  templateUrl: './model-validate.component.html',
  providers: [ModelValidateService],
  styleUrls: ['./model-validate.component.css'],
})
export class ModelValidateComponent {
  @Input() modelId: number | undefined;
  libraries: Library[] = [];
  selectedLibrary = new FormControl(undefined, [Validators.required]);
  validationResponse = "";

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
  }

  validate(): void{
    if (!!this.modelId && this.selectedLibrary.value.id){
      this.modelValidateService.validateModel(this.modelId, this.selectedLibrary.value.id).subscribe(res => {
        this.validationResponse = res;
      })
    }
  }
}
