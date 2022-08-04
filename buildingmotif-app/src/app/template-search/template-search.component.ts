import { Component, OnInit } from '@angular/core';
import { TemplateSearchService, Template } from './template-search.service';

@Component({
  selector: 'app-template-search',
  templateUrl: './template-search.component.html',
  styleUrls: [ './template-search.component.css' ],
  providers: [TemplateSearchService],
})
export class TemplateSearchComponent implements OnInit{
  error: any = undefined;
  templates: Template[] = [];

  constructor(private TemplateSearchService: TemplateSearchService) { }

  getAllTemplates() {
    this.TemplateSearchService.getAllTemplates()
      .subscribe({
        next: (data: Template[]) => {this.templates = data}, // success path
        error: (error) => this.error = error // error path  
      });
  }

  ngOnInit() {
    this.getAllTemplates()
    console.log("template-search")
  }
}
