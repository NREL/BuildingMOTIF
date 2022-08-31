import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Model } from '../types';

@Component({
  selector: 'app-model-search',
  templateUrl: './model-search.component.html',
  styleUrls: ['./model-search.component.css']
})
export class ModelSearchComponent implements OnInit {
  models: Model[] = [];

  constructor(private route: ActivatedRoute) {
    this.models = this.route.snapshot.data["ModelSearchResolver"]
  }

  ngOnInit(): void {
  }

}
