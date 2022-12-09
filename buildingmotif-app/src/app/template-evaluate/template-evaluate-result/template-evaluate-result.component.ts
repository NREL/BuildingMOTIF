import { Component, Input } from '@angular/core';
import { FormControl, Validators } from '@angular/forms';
import { ModelDetailService } from 'src/app/model-detail/model-detail.service';
import { Model } from 'src/app/types';
import {Router} from "@angular/router"

@Component({
  selector: 'app-template-evaluate-result',
  templateUrl: './template-evaluate-result.component.html',
  styleUrls: ['./template-evaluate-result.component.css'],
  providers: [ModelDetailService]
})
export class TemplateEvaluateResultComponent {
  @Input() evaluateTemplate?: string;
  @Input() models?: Model[];
  selectedModel = new FormControl(undefined, [Validators.required]);

  codeMirrorOptions: any = {
    theme: 'material',
    mode: 'application/xml',
    lineNumbers: true,
    lineWrapping: true,
    foldGutter: true,
    gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter', 'CodeMirror-lint-markers'],
    autoCloseBrackets: true,
    matchBrackets: true,
    lint: true,
    readOnly: true
  };

  constructor(private router: Router, private modelDetailService: ModelDetailService) { }

  addToModel(){
    if (this.evaluateTemplate == undefined) return // we shouldn't hit this
    this.modelDetailService.updateModelGraph(this.selectedModel.value.id, this.evaluateTemplate, true).subscribe(() => {
      this.router.navigate([`/models/${this.selectedModel.value.id}`])
    })
  }

}
