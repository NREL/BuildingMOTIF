import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { Observable, of } from 'rxjs';
import { ModelSearchService } from './model-search.service';
import { Model } from '../types'

@Injectable({
  providedIn: 'root'
})
export class ModelSearchResolver implements Resolve<Model[]> {

  constructor(private modelSearchService: ModelSearchService) {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<Model[]> {
    return this.modelSearchService.getAllModels()
  }
}
