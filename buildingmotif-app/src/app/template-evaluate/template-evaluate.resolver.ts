import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { Observable, of } from 'rxjs'
import { TemplateDetailService } from '../template-detail/template-detail.service';
import { Template } from '../types'

@Injectable({
  providedIn: 'root'
})
export class TemplateEvaluateResolver implements Resolve<Template> {

  constructor(private templateDetailService: TemplateDetailService) {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<Template> {
    const id = route.paramMap.get('id') ?? "-1"
    const idInt = parseInt(id);

    return this.templateDetailService.getTemplate(idInt, true);
  }
}
