import { Component, OnInit, Inject } from '@angular/core';
import { FormControl } from '@angular/forms';
import { PointlabelParserService } from './pointlabel-parser.service'
import { MatDialog, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { ModelSearchService } from '../model-search/model-search.service';
import { Model } from '../types';

export interface Token {
  error?: string;
  length: Number;
  token: string;
  value: string;
  id: string
}

export interface IProgram {
  name: string;
  xmlData: string;
}

export interface TokenizePointLabel {
  _errors: String[];
  success: Boolean;
  tokens: Token[]
}

declare var Blockly: any;

@Component({
  selector: 'app-pointlabel-parser',
  templateUrl: './pointlabel-parser.component.html',
  providers: [PointlabelParserService],
  styleUrls: ['./pointlabel-parser.component.css']
})
export class PointlabelParserComponent implements OnInit {
  workspace: any;
  // program: IProgram;
  pointLabelsFormControl: FormControl = new FormControl('[]'); // graph as in UI
  results: TokenizePointLabel[] = [];
  codeMirrorOptions: any = {
    // theme: 'material',
    mode: 'application/ld+json',
    lineNumbers: true,
    lineWrapping: true,
    foldGutter: true,
    gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter', 'CodeMirror-lint-markers'],
    autoCloseBrackets: true,
    matchBrackets: true,
    lint: true
  };

  constructor(private PointlabelParserService: PointlabelParserService, public dialog: MatDialog) {
  }

  ngOnInit(): void {
    this.workspace = Blockly.inject('blocklyDiv', {
      toolbox: document.getElementById('toolbox'),
      scrollbars: false
    });

    const state: string | null = localStorage.getItem('state')
    if (state) Blockly.serialization.workspaces.load(JSON.parse(state), this.workspace);

    const pointLabels: string | null = localStorage.getItem('pointLabels')
    if (pointLabels) this.pointLabelsFormControl.setValue(JSON.parse(pointLabels))

  }

  file: any;
  fileChanged(e: any) {
    this.file = e.target.files[0];
    let fileReader = new FileReader();
    fileReader.onload = (e: any) => {
      // read file
      const abbs: { s: string, type_name: string }[] = e.target.result.split(/\r?\n/).map((row: string) => {
        const items = row.split(",")
        return { s: items[0], type_name: items[1] }
      })

      // make choice
      var parentBlock = this.workspace.newBlock('choice');
      parentBlock.initSvg();
      parentBlock.render();
      var parentConnection = parentBlock.getInput('parsers').connection;

      // for each abb
      let currentConnection = parentConnection;
      abbs.forEach(abb => {
        // make child
        var childBlock = this.workspace.newBlock('string-url');
        childBlock.setFieldValue(abb.type_name, 'type_name');
        childBlock.setFieldValue(abb.s, 's');
        childBlock.initSvg();
        childBlock.render();
        var childConnection = childBlock.previousConnection;

        // connect child
        currentConnection.connect(childConnection);
        currentConnection = childBlock.nextConnection
      });
    }
    fileReader.readAsText(this.file);



  }

  openDialog(): void {
    const dialogRef = this.dialog.open(DialogOverviewExampleDialog, {
      width: '250px',
      data: { selectedModelId: null },
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result !== null && result !== undefined) {
        this.PointlabelParserService.getPointNames(
          result
        )
          .subscribe({
            next: (data: string[]) => {
              this.pointLabelsFormControl.setValue(JSON.stringify(data))
            }, // success path
            error: (error) => {
            }, // error path
          });
      }
    });
  }

  onHover(token: Token) {
    this.workspace.highlightBlock(token.id)
  }

  block_to_json(block: any): any {
    const res: any = {
      parser: block.type.split("-")[0],
      args: { id: block.id }
    }

    // set non nesting args
    Object.assign(res["args"], block.fields)

    // set nesting args
    if (block.inputs) {
      const parers = Object.keys(block.inputs).reduce((acc, key) => {
        acc[key] = this.block_list_to_json(block.inputs[key].block)
        return acc
      }, {} as any)
      Object.assign(res["args"], parers)
    }

    return res
  }

  block_list_to_json(block: any): any {
    let res: any = []
    do {
      res = [...res, this.block_to_json(block)]
      block = block.next?.block;
    } while (block);

    return res
  }

  parse() {
    const state = Blockly.serialization.workspaces.save(this.workspace);
    localStorage.setItem('state', JSON.stringify(state))
    localStorage.setItem('pointLabels', JSON.stringify(this.pointLabelsFormControl.value))

    const parser = this.block_to_json(state.blocks.blocks[0])

    this.PointlabelParserService.parse(
      JSON.parse(this.pointLabelsFormControl.value),
      parser
    )
      .subscribe({
        next: (data: TokenizePointLabel[]) => {
          this.results = data
        }, // success path
        error: (error) => {
        }, // error path
      });
  }

}

export interface DialogData {
  selectedModelId?: number;
}

@Component({
  selector: 'dialog-overview-example-dialog',
  templateUrl: 'dialog-overview-example-dialog.html',
  providers: [ModelSearchService],
})
export class DialogOverviewExampleDialog implements OnInit {
  models: Model[] = [];
  constructor(
    public dialogRef: MatDialogRef<DialogOverviewExampleDialog>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private modelSearchService: ModelSearchService,
  ) { }

  ngOnInit() {
    this.modelSearchService.getAllModels()
      .subscribe({
        next: (data: Model[]) => this.models = data, // success path
        error: (error) => { } // error path
      });
  }

  onClick(): void {
    this.dialogRef.close();
  }

  onNoClick(): void {
    this.dialogRef.close();
  }
}