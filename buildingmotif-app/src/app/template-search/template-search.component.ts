import { Component, OnInit } from '@angular/core';
import { TemplateSearchService, Template } from './template-search.service';
import {FormControl} from '@angular/forms';
import {Observable} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

@Component({
  selector: 'app-template-search',
  templateUrl: './template-search.component.html',
  styleUrls: [ './template-search.component.css' ],
  providers: [TemplateSearchService],
})
export class TemplateSearchComponent implements OnInit{
  error: any = undefined;
  templates: Template[] | undefined = undefined;
  fitlerStringControl = new FormControl('');
  filteredTemplates: Observable<Template[]> = new Observable();

  constructor(private TemplateSearchService: TemplateSearchService){}

  private _setTemplates(data: Template[]): void {
    this.templates = data;
    this.filteredTemplates = this.fitlerStringControl.valueChanges.pipe(
      startWith(''),
      map(value => this._filterTemplatesByName(value || '')),
    );
  }

  private _filterTemplatesByName(value: string): Template[] {
    const filterValue = value.toLowerCase();
    if(this.templates == undefined) return [];
    return this.templates.filter(template => template.name.toLocaleLowerCase().includes(filterValue))
  }

  ngOnInit() {
    this.TemplateSearchService.getAllTemplates()
      .subscribe({
        next: (data: Template[]) => this._setTemplates(data), // success path
        error: (error) => this.error = error // error path
      });
  }
}
