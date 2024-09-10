import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HttpErrorResponse, HttpResponse } from '@angular/common/http';

import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { handleError } from '../handle-error';

const API_URL = environment.API_URL;

export interface Template {
  name: string;
  id: number;
  body_id: number;
  optional_args: string[];
  library_id: string;
  dependency_ids: number[];
}

@Injectable()
export class TemplateDetailService {

  constructor(private http: HttpClient) { }

  getTemplate(id: number, includeParameters: boolean =false) {
    return this.http.get<Template>(API_URL + `/templates/${id}?parameters=${includeParameters}`)
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(handleError) // then handle the error
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
