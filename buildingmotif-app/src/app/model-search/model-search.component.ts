import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Model } from '../types';
import {FormControl} from '@angular/forms';
import {map, startWith} from 'rxjs/operators';
import {Observable} from 'rxjs';

@Component({
  selector: 'app-model-search',
  templateUrl: './model-search.component.html',
  styleUrls: ['./model-search.component.css']
})
export class ModelSearchComponent implements OnInit{
  models: Model[] = [];
  filteredModels: Observable<Model[]> = new Observable();
  fitlerStringControl: FormControl = new FormControl('')

  constructor(private route: ActivatedRoute) {
    this.models = this.route.snapshot.data["ModelSearchResolver"]
  }

  private _filterModelsByDescription(value: string): Model[] {

    return this.models.filter(model => model.description.toLocaleLowerCase().includes(value))
  }

  ngOnInit() {
    this.filteredModels = this.fitlerStringControl.valueChanges.pipe(
      startWith(''),
      map(value => this._filterModelsByDescription(value || '')),
    )
  }
}
