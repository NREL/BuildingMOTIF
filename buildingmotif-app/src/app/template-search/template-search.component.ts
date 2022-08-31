import { Component, OnInit } from '@angular/core';
import { TemplateSearchService, Template } from './template-search.service';
import {FormControl} from '@angular/forms';
import {Observable} from 'rxjs';
import {map, startWith} from 'rxjs/operators';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-template-search',
  templateUrl: './template-search.component.html',
  styleUrls: [ './template-search.component.css' ],
  providers: [TemplateSearchService],
})
export class TemplateSearchComponent implements OnInit{
  templates: Template[] = [];
  fitlerStringControl = new FormControl('');
  filteredTemplates: Observable<Template[]> = new Observable();

  constructor(private route: ActivatedRoute) {
    this.templates = this.route.snapshot.data["templateSearch"];
  }

  private _filterTemplatesByName(value: string): Template[] {
    const filterValue = value.toLowerCase();

    return this.templates.filter(template => template.name.toLocaleLowerCase().includes(filterValue))
  }

  ngOnInit() {
    this.filteredTemplates = this.fitlerStringControl.valueChanges.pipe(
      startWith(''),
      map(value => this._filterTemplatesByName(value || '')),
    );
  }
}
