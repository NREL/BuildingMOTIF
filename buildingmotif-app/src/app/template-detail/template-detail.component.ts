import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common';
import { Template } from '../types'
import {TemplateDetailService} from './template-detail.service'

@Component({
  selector: 'app-template-detail',
  templateUrl: './template-detail.component.html',
  providers: [TemplateDetailService],
  styleUrls: ['./template-detail.component.css']
})
export class TemplateDetailComponent implements OnInit {
  error: any
  id: number | undefined;
  template: Template | undefined;

  constructor(
    private route: ActivatedRoute,
    private location: Location,
    private TemplateDetailService: TemplateDetailService,
  ) {}

  getTemplate(id: number) {
    this.TemplateDetailService.getTemplate(id)
      .subscribe({
        next: (data: Template) => {this.template = data}, // success path
        error: (error) => this.error = error // error path  
      });
  }

  ngOnInit(): void {
    this.id = parseInt(this.route.snapshot.paramMap.get('id')!, 10);
    this.getTemplate(this.id);
  }

}
