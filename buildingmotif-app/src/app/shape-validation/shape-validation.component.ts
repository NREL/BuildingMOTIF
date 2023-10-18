import { Component, OnInit, Input} from '@angular/core';
import { LibraryService, Shape } from '../library/library.service';
import { ModelDetailService } from '../model-detail/model-detail.service';
import {ShapeValidationService} from './shape-validate.service';
import { ValidationResponse } from '../model-validate/model-validate.service';

@Component({
  selector: 'app-shape-validation',
  templateUrl: './shape-validation.component.html',
  providers: [LibraryService, ModelDetailService, ShapeValidationService],
  styleUrls: ['./shape-validation.component.css']
})
export class ShapeValidationComponent implements OnInit {
  @Input() modelId: number | undefined;
  showGettingShapesSpinner = false;
  showValidatingSpinner = false;
  shapes?:  {[definition_type: string]: Shape[]} = undefined;
  selected: Record<number, Set<string>> = {};
  targetNodes?: string[] = undefined;
  selectedTargetNode?: string = undefined;
  response?: Record<string, string[]> = undefined;


  constructor(private libraryService: LibraryService, private modelDetailService: ModelDetailService, private shapeValidationService: ShapeValidationService) {}

  ngOnInit(): void {
    this.showGettingShapesSpinner = true;
    this.libraryService.getAllShapes().subscribe(
      res => {
        this.shapes = res;
      },
      err => {},
      () => {this.showGettingShapesSpinner = false},
    );

    if (this.modelId === undefined) return;
    this.modelDetailService.getTargetNodes(this.modelId).subscribe(
      res => {
        this.targetNodes = res;
      },
      err => {},
    );
  }

  toggle_selected(shape: Shape): void {
    var {shape_collection_id, shape_uri} = shape;

    // add shape_collection if not there
    if (!(shape_collection_id in this.selected)){
      this.selected[shape.shape_collection_id] = new Set([shape.shape_uri]);
      return 
    }

    const shape_uri_set = this.selected[shape.shape_collection_id]
    // add shape_uri if not there
    if (!shape_uri_set.has(shape.shape_uri)) {
      shape_uri_set.add(shape.shape_uri)
      return
    }

    // it's there! delete
    shape_uri_set.delete(shape.shape_uri)
    if (shape_uri_set.size == 0) {
      delete this.selected[shape.shape_collection_id]
    }
  }

  validate(){
    if (this.modelId === undefined) return;
    if (this.selectedTargetNode === undefined) return;

    const modelId = this.modelId;
    const shape_collection_ids = Object.keys(this.selected).map(Number);
    const shape_uris =  Object.values(this.selected).reduce(
      (a, c) => a.concat([...c]), 
      [] as string[]
    );
    const target_class = this.selectedTargetNode[0]

    this.showValidatingSpinner = true;
    this.shapeValidationService.validateModelShape(modelId, shape_collection_ids, shape_uris, target_class).subscribe(
      res => {
        this.response = res;
        console.log(this.response)
      },
      err => {},
      () => {this.showValidatingSpinner = false}
    );
  }
}
