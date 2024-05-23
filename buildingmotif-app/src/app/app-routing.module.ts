import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TemplateSearchComponent } from '../app/template-search/template-search.component'
import { TemplateDetailComponent } from '../app/template-detail/template-detail.component'
import { ModelSearchComponent } from '../app/model-search/model-search.component'
import { ModelSearchResolver } from '../app/model-search/model-search.resolver'
import { ModelDetailComponent } from '../app/model-detail/model-detail.component'
import { ModelDetailResolver } from '../app/model-detail/model-detail.resolver'
import { TemplateEvaluateComponent} from './template-evaluate/template-evaluate.component'
import { TemplateEvaluateResolver} from './template-evaluate/template-evaluate.resolver'
import { ModelNewComponent } from '../app/model-new/model-new.component'
import { PointlabelParserComponent } from '../app/pointlabel-parser/pointlabel-parser.component'

const routes: Routes = [
  { path: 'pointlabel_parser', component: PointlabelParserComponent},
  { path: 'models/new', component: ModelNewComponent},
  { path: 'templates/:id', component: TemplateDetailComponent },
  { path: 'templates/:id/evaluate', component: TemplateEvaluateComponent, resolve: {TemplateEvaluateResolver}},
  { path: 'models/:id', component: ModelDetailComponent, resolve: {ModelDetailResolver}},
  { path: 'templates', component: TemplateSearchComponent},
  { path: 'models', component: ModelSearchComponent, resolve: {ModelSearchResolver}},
  { path: '',   redirectTo: '/templates', pathMatch: 'full' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
