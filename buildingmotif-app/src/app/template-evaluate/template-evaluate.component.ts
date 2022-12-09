import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ModelSearchService } from '../model-search/model-search.service';
import { Model, Template } from '../types';
import { TemplateEvaluateService } from './template-evaluate.service';

@Component({
  selector: 'app-template-evaluate',
  templateUrl: './template-evaluate.component.html',
  styleUrls: ['./template-evaluate.component.css'],
  providers: [TemplateEvaluateService, ModelSearchService]
})
export class TemplateEvaluateComponent {
  state: "FORM" | "RESULT" = "FORM";
  template: Template;
  evaluatedGraph?: string;
  models: Model[] = []

  constructor(
    private route: ActivatedRoute,
    private templateEvaluateService: TemplateEvaluateService,
    private modelSearchService: ModelSearchService
  ) {
    this.template = this.route.snapshot.data["TemplateEvaluateResolver"];
  }

   parameterFormValuesEvent(parameterFormValues: {[name: string]: string}): void {
    const evaluateTemplate = this.templateEvaluateService.evaluateTemplate(this.template.id, parameterFormValues);
    evaluateTemplate.subscribe((result) => {
      this.evaluatedGraph = result
      this.state = "RESULT";
    });

    this.modelSearchService.getAllModels().subscribe((models) => {
      this.models = models;
    });
  }

}
