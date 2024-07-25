import { Component, OnInit } from '@angular/core';
import { FormControl } from '@angular/forms';
import { PointlabelParserService } from './pointlabel-parser.service'

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

export interface JsonParser  {
  parser: string;
  id?: string;
  args: {id?: string, parsers?: JsonParser[], type_name?: string, s?: string, length?: number};
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

    const state: string | null = localStorage.getItem('state')
    if (state) Blockly.serialization.workspaces.load(JSON.parse(state), this.workspace);

    const pointLabels: string | null = localStorage.getItem('pointLabels')
    if (pointLabels) this.pointLabelsFormControl.setValue(JSON.parse(pointLabels))
  }

  defaultFill() {
    // this is a place holder input
    const json_parser: JsonParser = {"parser":"sequence","args":{"id":"$bh|H!ZDhv943E?;JTBR","parsers":[{"parser":"choice","args":{"id":"XaiW~OaA(1bqpAJmN$;P","parsers":[{"parser":"string","args":{"id":"8,sqLaZcdBIx?W;=i(Yd","type_name":"A","s":"B"}},{"parser":"string","args":{"id":"sd)kp8fJeJ/jCSE:Gp}h","type_name":"C","s":"D"}}]}},{"parser":"string","args":{"id":"u`Y?LS?N#h29~5l6VRs)","type_name":"Delimiter","s":"E"}},{"parser":"choice","args":{"id":"9J|Gl4K$,l?je*/jRRTa","parsers":[{"parser":"sequence","args":{"id":"v1srsf/1,=y9p3!nPq8M","parsers":[{"parser":"string","args":{"id":"Sx-V|ff/#S=W%B`j}1cM","type_name":"F","s":"G"}},{"parser":"substring_n","args":{"id":"{N*Phycp(glt`a*2TEWN","type_name":"H","length":1}}]}},{"parser":"sequence","args":{"id":"fw|3:6YeVyvest[@a4kC","parsers":[{"parser":"string","args":{"id":"F^v+jRh2@OlN4[dEfQNa","type_name":"I","s":"J"}},{"parser":"substring_n","args":{"id":"lL,KvAksa7j:.IwV,)}?","type_name":"K","length":2}}]}}]}}]}};

    // its important this is a sequence
    if (json_parser.parser !== "sequence") return 

    json_parser.parser = "sequence-wrapper"
    this.jsonToBlock(json_parser)
  }

  jsonToBlock(json_parser: JsonParser){
    const {parser, args} = json_parser;

    // get parser name
    let parser_name;
    if (parser == "string") parser_name = "string-url"
    else if (parser == "sequence") parser_name = "sequence-internal"
    else parser_name = parser

    // build parent block
    var parentBlock = this.workspace.newBlock(parser_name);
    const {id, parsers, ...field_values} = args;
    Object.entries(field_values).forEach(([field, value]) => {parentBlock.setFieldValue(value, field)});
    parentBlock.initSvg();
    parentBlock.render(); 
    var parentConnection = parentBlock.getInput('parsers')?.connection;

    // build out children
    let currentConnection = parentConnection;
    args.parsers?.forEach(p => {
      const childBlock = this.jsonToBlock(p)

      // connect child
      var childConnection = childBlock.previousConnection;
      currentConnection.connect(childConnection);
      currentConnection = childBlock.nextConnection
    });

    return parentBlock
  }

  file: any;
  fileChanged(e: any) {
    this.file = e.target.files[0];
    let fileReader = new FileReader();
    fileReader.onload = (e: any) => {
      // read file
      const abbs: {s: string, type_name: string}[] = e.target.result.split(/\r?\n/).map((row: string) => {
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
