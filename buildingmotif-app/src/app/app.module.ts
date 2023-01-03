import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LibraryComponent } from './library/library.component';
import { TemplateSearchComponent } from './template-search/template-search.component';
import { HttpClientModule } from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import {MatSelectModule} from '@angular/material/select'; 
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {MatDividerModule} from '@angular/material/divider'; 
import {MatListModule} from '@angular/material/list';
import { TemplateDetailComponent } from './template-detail/template-detail.component'; 
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatAutocompleteModule} from '@angular/material/autocomplete'; 
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from "@angular/material/form-field";
import {MatIconModule} from '@angular/material/icon';
import { ModelSearchComponent } from './model-search/model-search.component';
import { MenuComponent } from './menu/menu.component'; 
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatButtonModule} from '@angular/material/button';
import { ModelDetailComponent } from './model-detail/model-detail.component'; 
import {MatSnackBarModule} from '@angular/material/snack-bar'; 
import { CodemirrorModule } from '@ctrl/ngx-codemirror';
import {MatCardModule} from '@angular/material/card';
import { TemplateEvaluateFormComponent } from './template-evaluate/template-evaluate-form/template-evaluate-form.component'; 
import { TemplateDetailService } from './template-detail/template-detail.service';
import {MatTableModule} from '@angular/material/table';
import { TemplateEvaluateResultComponent } from './template-evaluate/template-evaluate-result/template-evaluate-result.component'; 
import { TemplateEvaluateComponent} from './template-evaluate/template-evaluate.component'
import { ModelNewComponent } from './model-new/model-new.component'; 
import { ModelValidateComponent } from './model-validate/model-validate.component';
import { LibraryService } from './library/library.service';

@NgModule({
  declarations: [
    AppComponent,
    LibraryComponent,
    TemplateSearchComponent,
    TemplateDetailComponent,
    ModelSearchComponent,
    MenuComponent,
    ModelDetailComponent,
    TemplateEvaluateComponent,
    TemplateEvaluateFormComponent,
    TemplateEvaluateResultComponent,
    ModelNewComponent,
    ModelValidateComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    BrowserAnimationsModule,
    MatSelectModule,
    FormsModule, 
    ReactiveFormsModule,
    MatDividerModule,
    MatListModule,
    MatProgressBarModule,
    MatAutocompleteModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatToolbarModule,
    MatButtonModule,
    MatSnackBarModule,
    CodemirrorModule,
    MatCardModule,
    MatTableModule
  ],
  providers: [TemplateDetailService, LibraryService],
  bootstrap: [AppComponent]
})
export class AppModule { }
