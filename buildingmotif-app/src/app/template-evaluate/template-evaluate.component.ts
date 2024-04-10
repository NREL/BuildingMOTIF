import { Component, OnInit, Inject, Input, ViewChild } from '@angular/core';
import { Template } from '../types';
import { TemplateEvaluateService } from './template-evaluate.service';
import { TemplateDetailService } from '../template-detail/template-detail.service';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatStepper } from '@angular/material/stepper';

export interface DialogData {
  templateId: number;
  modelId: number;
}

@Component({
  selector: 'app-template-evaluate',
  templateUrl: './template-evaluate.component.html',
  styleUrls: ['./template-evaluate.component.css'],
  providers: [TemplateDetailService, TemplateEvaluateService]
})
export class TemplateEvaluateComponent implements OnInit {
  error: any = undefined;
  template: Template | undefined = undefined;
  evaluatedGraph?: string;
  modelId?: number;
  @ViewChild("stepper") stepper?: MatStepper;

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private templateDetailService: TemplateDetailService,
    private templateEvaluateService: TemplateEvaluateService,
  ) {}

  ngOnInit() {
    this.modelId = this.data.modelId;

    this.templateDetailService.getTemplate(this.data.templateId)
    .subscribe({
      next: (template: Template) => {
        this.template = template
      }, // success path
      error: (error) => this.error = error // error path
    });
  }

  parameterFormValuesEvent(parameterFormValues: {[name: string]: string}): void {
    if (this.template == undefined) return;
    if (this.modelId == undefined) return;

    const evaluateTemplate = this.templateEvaluateService.evaluateTemplateBindings(this.template.id, this.modelId, parameterFormValues);
    evaluateTemplate.subscribe((result) => {
      this.evaluatedGraph = result;
      this.stepper?.next();
    });
  }

  ingressFileEvent(file: File): void {
    if (this.template == undefined) return;
    if (this.modelId == undefined) return;

    const evaluateTemplate = this.templateEvaluateService.evaluateTemplateIngress(this.template.id, this.modelId, file);
    evaluateTemplate.subscribe((result) => {
      this.evaluatedGraph = result;
      this.stepper?.next();
    });
  }

}
