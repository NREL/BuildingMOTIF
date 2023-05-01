import { Component, Input } from '@angular/core';
import { ModelDetailService } from 'src/app/model-detail/model-detail.service';

@Component({
  selector: 'app-template-evaluate-result',
  templateUrl: './template-evaluate-result.component.html',
  styleUrls: ['./template-evaluate-result.component.css'],
  providers: [ModelDetailService]
})
export class TemplateEvaluateResultComponent {
  @Input() evaluateTemplate?: string;
  @Input() modelId?: number;

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

  constructor(private modelDetailService: ModelDetailService) { }

  addToModel(){
    if (this.modelId == undefined) return // we shouldn't hit this
    if (this.evaluateTemplate == undefined) return // we shouldn't hit this

    this.modelDetailService.updateModelGraph(this.modelId, this.evaluateTemplate, true).subscribe(() => {
      location.reload();
    })
  }

}
