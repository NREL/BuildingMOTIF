import { Component, OnInit } from '@angular/core';
import {FormControl} from '@angular/forms';
import {PointlabelParserService} from './pointlabel-parser.service'

export interface Token {
  error?: string;
  length: Number;
  token: string;
  value: string;
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

  constructor(private PointlabelParserService: PointlabelParserService,) {
   }

  ngOnInit(): void {
    this.workspace = Blockly.inject('blocklyDiv', {
      toolbox: document.getElementById('toolbox'),
      scrollbars: false
    });
  }

  block_to_json(block: any): any {
    const res: any = { name: block.type, args: {} }

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
    } while(block);

    return res
  }

  parse(){
    const state = Blockly.serialization.workspaces.save(this.workspace);
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
        console.log(error)
      }, // error path
    });
  }

}
