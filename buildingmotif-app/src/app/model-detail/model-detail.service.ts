import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Model } from '../types'
import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class ModelDetailService {

  constructor(private http: HttpClient) { }

  getModel(id: number) {
    return this.http.get<Model>(`http://localhost:5000/models/${id}`)
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(this.handleError) // then handle the error
      );
  }

  getModelGraph(id: number) {
    return this.http.get(`http://localhost:5000/models/${id}/graph`, {responseType: 'text'})
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(this.handleError) // then handle the error
      );
  }

  updateModelGraph(id: number, newGraph: string, append: boolean = false) {
    const headers = {'Content-Type': "application/xml"}

    return this.http[append? "patch": "put"](`http://localhost:5000/models/${id}/graph`, newGraph, {headers, responseType: 'text'})
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
