import { Component, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Model } from '../types'
import { ModelDetailService, Triple } from './model-detail.service'
import { FormControl } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import {MatDialog} from '@angular/material/dialog';
import {TemplateEvaluateComponent} from '../template-evaluate/template-evaluate.component'
import {MatSort, Sort, MatSortModule, } from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';

@Component({
  selector: 'app-model-detail',
  templateUrl: './model-detail.component.html',
  providers: [ModelDetailService],
  styleUrls: ['./model-detail.component.css']
})
export class ModelDetailComponent implements OnInit{
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
  updatingGraphSpinner: boolean = false;
  tableData = new MatTableDataSource<Triple>();
  displayedColumns = ["parent", "ptype", "child", "ctype"];
  columnsToDisplay = ["parent", "ptype", "child", "ctype"];

  constructor(
    private route: ActivatedRoute,
    private ModelDetailService: ModelDetailService,
    private _snackBar: MatSnackBar,
    public dialog: MatDialog,
  ) {
    [this.model, this.graph] = route.snapshot.data["ModelDetailResolver"];
    this.graphFormControl.setValue(this.graph);
  }

  @ViewChild(MatSort) sort: MatSort | null = null;

  ngOnInit() {
    this.ModelDetailService.getModelTable(this.model.id)
      .subscribe({
        next: (data: Triple[]) => {
          this.tableData = new MatTableDataSource(data);
          this.tableData.sort = this.sort;
        }, // success path
        error: (error) => {} // error path  
      });
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
    this.updatingGraphSpinner = true;
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
        this.updatingGraphSpinner = false;
      }
    });
  }
}
