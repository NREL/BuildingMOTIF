import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HttpErrorResponse } from '@angular/common/http';
import { Model } from '../types'
import { throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { handleError } from '../handle-error';

const API_URL = environment.API_URL;

@Injectable({
  providedIn: 'root'
})
export class ShapeValidationService {

  constructor(private http: HttpClient) { }

  validateModelShape(modelId: number, shape_collection_ids: number[], shape_uris: string[], target_class: string) {
    const headers = {'Content-Type': "application/json"}

    return this.http.post<Record<string, string[]>>(API_URL + `/models/${modelId}/validate_shape`,
        {shape_collection_ids, shape_uris, target_class},
        {headers, responseType: 'json'}
      )
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

export interface ValidationResponse {
    valid: boolean;
    message: string;
    reasons: string[];
}
