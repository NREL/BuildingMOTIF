import { Component, OnInit } from '@angular/core';
import { Library, Template, LibraryService } from './library.service';
import { MatSelectChange } from '@angular/material/select';

@Component({
  selector: 'app-library',
  templateUrl: './library.component.html',
  providers: [LibraryService],
})
export class LibraryComponent implements OnInit {
  error: any;
  libraries: {
    viewValue: string;
    value: Library;
  }[] | undefined;
  selectedLibrary: Library | undefined = undefined;

  constructor(private libraryService: LibraryService) { }

  getAllLibraries() {
    this.libraryService.getAllLibraries()
      .subscribe({
        next: (data: Library[]) => {
          this.libraries = data.map(lib => {
            return {
              value: lib,
              viewValue: lib.name
            }
          })
        }, // success path
        error: (error) => this.error = error // error path  
      });
  }

  getLibrarysTemplates(library_id: number){
    this.libraryService.getLibrarysTemplates(library_id)
      .subscribe({
        next: (library) => {
          if (this.selectedLibrary){
            this.selectedLibrary.templates = library.templates
          }
        },
        error: (error) => this.error = error // error path  
      })
  }

  onSelectedLibraryChange(event: MatSelectChange) {
    if (this.selectedLibrary){
      this.getLibrarysTemplates(this.selectedLibrary?.id)
    }
  }

  ngOnInit() {
    this.getAllLibraries()
  }
}
