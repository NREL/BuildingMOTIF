import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TemplateSearchComponent } from '../app/template-search/template-search.component'
import { TemplateSearchResolver } from '../app/template-search/template-search.resolver'
import { TemplateDetailComponent } from '../app/template-detail/template-detail.component'
import { ModelSearchComponent } from '../app/model-search/model-search.component'
import { ModelSearchResolver } from '../app/model-search/model-search.resolver'
import { ModelDetailComponent } from '../app/model-detail/model-detail.component'
import { ModelDetailResolver } from '../app/model-detail/model-detail.resolver'

const routes: Routes = [
  { path: 'templates/:id', component: TemplateDetailComponent },
  { path: 'models/:id', component: ModelDetailComponent, resolve: {ModelDetailResolver} },
  { path: 'templates', component: TemplateSearchComponent, resolve: {templateSearch:TemplateSearchResolver}},
  { path: 'models', component: ModelSearchComponent, resolve: {ModelSearchResolver}},
  { path: '',   redirectTo: '/templates', pathMatch: 'full' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
