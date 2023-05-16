import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Model } from '../types'
import { ModelDetailService } from './model-detail.service'
import {FormControl} from '@angular/forms';
import {
  MatSnackBar,
  MatSnackBarHorizontalPosition,
  MatSnackBarVerticalPosition,
} from '@angular/material/snack-bar';
import {MatDialog} from '@angular/material/dialog';
import {TemplateEvaluateComponent} from '../template-evaluate/template-evaluate.component'

@Component({
  selector: 'app-model-detail',
  templateUrl: './model-detail.component.html',
  providers: [ModelDetailService],
  styleUrls: ['./model-detail.component.css']
})
export class ModelDetailComponent{
  model: Model;
  graph: string; // graph as in DB
  graphFormControl: FormControl = new FormControl(''); // graph as in UI
  codeMirrorOptions: any = {
    theme: 'material',
    mode: 'application/xml',
    lineNumbers: true,
    lineWrapping: true,
    foldGutter: true,
    gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter', 'CodeMirror-lint-markers'],
    autoCloseBrackets: true,
    matchBrackets: true,
    lint: true
  };
  showFiller: boolean = true;
  sideNaveOpen: boolean = false;
  updateingGraphSpinner: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private ModelDetailService: ModelDetailService,
    private _snackBar: MatSnackBar,
    public dialog: MatDialog,
  ) {
    [this.model, this.graph] = route.snapshot.data["ModelDetailResolver"];
    this.graphFormControl.setValue(this.graph);
  }

  onSave(): void{
    this.ModelDetailService.updateModelGraph(this.model.id, this.graphFormControl.value)
      .subscribe({
        next: (data: string) => {
          this.graph = data
          this.openSnackBar("success")
        }, // success path
        error: (error) => {
          this.openSnackBar("error")
          console.log(error)
        } // error path  
      });
  }

  openSnackBar(message: string) {
    this._snackBar.open(message, "close", {});
  }

  undoChangesToGraph(): void {
    this.graphFormControl.setValue(this.graph)
  }

  openEvaulateEvent(templateId: number): void {
    this.dialog.open(
      TemplateEvaluateComponent,
      {data: {templateId, modelId: this.model.id}}
    );
  }

  updateGraphWithFile(event: Event) {
    this.updateingGraphSpinner = true;
    const element = event.currentTarget as HTMLInputElement;
    let files: FileList | null = element.files;
    const fileToUpload = files?.item(0) ?? null;

    if (!fileToUpload) return;

    this.ModelDetailService.updateModelGraph(this.model.id, fileToUpload, true)
    .subscribe({
      next: (data: string) => {
        this.graph = data;
        this.graphFormControl.setValue(this.graph);
        this.openSnackBar("success")
      }, // success path
      error: (error) => {
        this.openSnackBar("error")
      }, // error path
      complete: () => {
        this.updateingGraphSpinner = false;
      }
    });
  }
}
