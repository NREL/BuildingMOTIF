import { Component, Input, OnInit } from '@angular/core';
import { Template } from '../../types';
import { ActivatedRoute } from '@angular/router';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-template-evaluate-form',
  templateUrl: './template-evaluate-form.component.html',
  styleUrls: ['./template-evaluate-form.component.css']
})
export class TemplateEvaluateFormComponent implements OnInit {
  @Input() template?: Template;

  displayedColumns: string[] = ['parameterName', 'parametersValueControl'];
  parametersForm: FormGroup = new FormGroup({});
  dataSource: {parameterName: string, parametersValueControl: FormControl}[] = [];

  @Output() parameterFormValuesEvent = new EventEmitter<{[name: string]: string}>();

  constructor() {}

  evaluateClicked(): void {
    this.parameterFormValuesEvent.emit(this.parametersForm.value);
  }

  ngOnInit(): void {
    if (this.template == undefined) return // We shouldn't trigger this.
    if (this.template.parameters == undefined) return // We shouldn't trigger this.

    const parameterControls: {[name: string]: FormControl} = this.template.parameters?.reduce((acc, curr) => {
      return  {...acc, [curr]: new FormControl("", Validators.required)}
    }, {})

    this.parametersForm = new FormGroup(parameterControls);
    this.dataSource = Object.entries(parameterControls).map(([parameterName, parametersValueControl]) => {
      return {parameterName, parametersValueControl}
    })
  }
}
