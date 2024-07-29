import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HttpErrorResponse, HttpResponse } from '@angular/common/http';

import { Observable, throwError } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { handleError } from '../handle-error';

const API_URL = environment.API_URL;

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
    return this.http.get<Library[]>(API_URL + `/libraries`)
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(handleError) // then handle the error
      );
  }

  getAllShapes() {
    return this.http.get<{[definition_type: string]: Shape[]}>(API_URL + `/libraries/shapes`)
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(handleError) // then handle the error
      );
  }

  getLibrarysTemplates(library_id: number) {
    return this.http.get<Library>(API_URL + `/libraries/${library_id}?expand_templates=True`)
      .pipe(
        retry(3), // retry a failed request up to 3 times
        catchError(handleError), // then handle the error
      );
  }
}
