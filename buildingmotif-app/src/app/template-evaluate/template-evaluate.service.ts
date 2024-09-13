import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HttpErrorResponse, HttpResponse } from '@angular/common/http';

import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';

export interface Template {
  name: string;
  id: number;
  body_id: number;
  optional_args: string[];
  library_id: string;
  dependency_ids: number[];
}

@Injectable()
export class TemplateEvaluateService {

  constructor(private http: HttpClient) { }

  evaluateTemplateBindings(templateId: number, modelId: number, parameters: {[name: string]: string}) {
    const bindings = Object.entries(parameters).reduce((acc, [name, value]) => {
      return {...acc, [name]: {"@id": value}}
    }, {})

    return this.http.post(
      `http://localhost:5000/templates/${templateId}/evaluate/bindings`,
      {model_id: modelId, bindings},
      {responseType: 'text'}
      )
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(this.handleError) // then handle the error
      );

  }

  evaluateTemplateIngress(templateId: number, modelId: number, file: File) {
    return this.http.post(
      `http://localhost:5000/templates/${templateId}/evaluate/ingress?model_id=${modelId}`,
      file,
      {responseType: 'text'}
      )
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(this.handleError) // then handle the error
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
