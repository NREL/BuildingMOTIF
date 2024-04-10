import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HttpErrorResponse, HttpResponse } from '@angular/common/http';

import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';

export interface Library {
  name: string;
  id: number;
  shape_collection_id: number;
  template_ids?: number[];
  templates?: Template[];
}

export interface Template {
  name: string;
  id: number;
  body_id: number;
  optional_args: string[];
  library_id: string;
  dependency_ids: number[];
}

export interface Shape {
  library_name: string;
  shape_uri: string;
  shape_collection_id: number
  label: string;
}

@Injectable()
export class LibraryService {

  constructor(private http: HttpClient) { }

  getAllLibraries() {
    return this.http.get<Library[]>("http://localhost:5000/libraries")
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(this.handleError) // then handle the error
      );
  }

  getAllShapes() {
    return this.http.get<{[definition_type: string]: Shape[]}>("http://localhost:5000/libraries/shapes")
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(this.handleError) // then handle the error
      );
  }

  getLibrarysTemplates(library_id: number) {
    return this.http.get<Library>(`http://localhost:5000/libraries/${library_id}?expand_templates=True`)
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(this.handleError), // then handle the error
      );
  }

 
  private handleError(error: HttpErrorResponse) {
    if (error.status === 0) {
      // A client-side or network error occurred. Handle it accordingly.
      console.error('An error occurred:', error.error);
    } else {
      // The backend returned an unsuccessful response code.
      // The response body may contain clues as to what went wrong.
      console.error(
        `Backend returned code ${error.status}, body was: `, error.error);
    }
    // Return an observable with a user-facing error message.
    return throwError(() => new Error(`${error.status}: ${error.error}`));
  }

}
