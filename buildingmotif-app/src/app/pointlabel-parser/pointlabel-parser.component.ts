import { Component, OnInit } from '@angular/core';
import {FormControl} from '@angular/forms';
import {PointlabelParserService} from './pointlabel-parser.service'

export interface Token {
  error?: string;
  length: Number;
  token: string;
  value: string;
}

export interface TokenizePointLabel {
  _errors: String[];
  success: Boolean;
  tokens: Token[]

}

@Component({
  selector: 'app-pointlabel-parser',
  templateUrl: './pointlabel-parser.component.html',
  providers: [PointlabelParserService],
  styleUrls: ['./pointlabel-parser.component.css']
})
export class PointlabelParserComponent implements OnInit {
  pointLabelsFormControl: FormControl = new FormControl('[]'); // graph as in UI
  parsersFormControl: FormControl = new FormControl('{}'); // graph as in UI
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

  constructor(private PointlabelParserService: PointlabelParserService,) { }

  ngOnInit(): void {
    
  }

  parse(){
    console.log(this.pointLabelsFormControl.value)
    console.log(this.parsersFormControl.value)
    this.PointlabelParserService.parse(JSON.parse(this.pointLabelsFormControl.value), JSON.parse(this.parsersFormControl.value))
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
