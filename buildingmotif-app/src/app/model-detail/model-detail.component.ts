import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common';
import { Model } from '../types'
import {ModelDetailService} from './model-detail.service'

@Component({
  selector: 'app-model-detail',
  templateUrl: './model-detail.component.html',
  providers: [ModelDetailService],
  styleUrls: ['./model-detail.component.css']
})
export class ModelDetailComponent implements OnInit {
  error: any
  id: number | undefined;
  model: Model | undefined;

  constructor(
    private route: ActivatedRoute,
    private location: Location,
    private ModelDetailService: ModelDetailService,
  ) {}

  getModel(id: number) {
    this.ModelDetailService.getModel(id)
      .subscribe({
        next: (data: Model) => {this.model = data}, // success path
        error: (error) => this.error = error // error path  
      });
  }

  ngOnInit(): void {
    this.id = parseInt(this.route.snapshot.paramMap.get('id')!, 10);
    this.getModel(this.id);
  }

}
