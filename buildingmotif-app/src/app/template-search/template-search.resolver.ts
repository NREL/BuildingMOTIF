import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { Observable, of } from 'rxjs';
import { TemplateSearchService, Template } from './template-search.service';

@Injectable({
  providedIn: 'root'
})
export class TemplateSearchResolver implements Resolve<Template[]> {

  constructor(private templateSearchService: TemplateSearchService) {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<Template[]> {
    return this.templateSearchService.getAllTemplates()
  }
}
