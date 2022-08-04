import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TemplateSearchComponent } from '../app/template-search/template-search.component'
import { TemplateDetailComponent } from '../app/template-detail/template-detail.component'

const routes: Routes = [
  { path: 'templates/:id', component: TemplateDetailComponent },
  { path: 'templates', component: TemplateSearchComponent },
  { path: '',   redirectTo: '/templates', pathMatch: 'full' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
