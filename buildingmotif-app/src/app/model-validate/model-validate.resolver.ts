import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { Observable, of } from 'rxjs';
import { Library, LibraryService } from '../library/library.service';

@Injectable({
  providedIn: 'root'
})
export class ModelValidateResolver implements Resolve<Library[]> {

  constructor(private libraryService: LibraryService) {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<Library[]> {
    return this.libraryService.getAllLibraries();
  }
}
