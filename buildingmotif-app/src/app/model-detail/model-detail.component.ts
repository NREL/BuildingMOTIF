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

  constructor(
    private route: ActivatedRoute,
    private ModelDetailService: ModelDetailService,
    private _snackBar: MatSnackBar,
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
    this._snackBar.open(message, "oh", {});
  }

  undoChangesToGraph(): void {
    this.graphFormControl.setValue(this.graph)
  }
}
