import { Component, Input, OnInit } from '@angular/core';
import { Template } from '../../types';
import { ActivatedRoute } from '@angular/router';
import { UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-template-evaluate-form',
  templateUrl: './template-evaluate-form.component.html',
  styleUrls: ['./template-evaluate-form.component.css']
})
export class TemplateEvaluateFormComponent implements OnInit {
  @Input() template?: Template;

  displayedColumns: string[] = ['parameterName', 'parametersValueControl'];
  parametersForm: UntypedFormGroup = new UntypedFormGroup({});
  dataSource: {parameterName: string, parametersValueControl: UntypedFormControl}[] = [];
  fileToUpload: File | null = null;

  @Output() parameterFormValuesEvent = new EventEmitter<{[name: string]: string}>();
  @Output() ingressFileEvent = new EventEmitter<File>();

  constructor() {}

  evaluateClicked(): void {
    this.parameterFormValuesEvent.emit(this.parametersForm.value);
  }

  handleFileInput(event: Event) {
    const element = event.currentTarget as HTMLInputElement;
    let files: FileList | null = element.files;
    this.fileToUpload = files?.item(0) ?? null;

    if(this.fileToUpload) this.ingressFileEvent.emit(this.fileToUpload);
  }

  ngOnInit(): void {
    if (this.template == undefined) return // We shouldn't trigger this.
    if (this.template.parameters == undefined) return // We shouldn't trigger this.

    const parameterControls: {[name: string]: UntypedFormControl} = this.template.parameters?.reduce((acc, curr) => {
      return  {...acc, [curr]: new UntypedFormControl("", Validators.required)}
    }, {})

    this.parametersForm = new UntypedFormGroup(parameterControls);
    this.dataSource = Object.entries(parameterControls).map(([parameterName, parametersValueControl]) => {
      return {parameterName, parametersValueControl}
    })
  }
}
