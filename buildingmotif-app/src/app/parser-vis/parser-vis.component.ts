import { Component, OnInit, Input} from '@angular/core';

@Component({
  selector: 'app-parser-vis',
  templateUrl: './parser-vis.component.html',
  styleUrls: ['./parser-vis.component.css']
})
export class ParserVisComponent implements OnInit {
  @Input() parser: any | undefined;

  constructor() { }

  ngOnInit(): void {
  }

}
