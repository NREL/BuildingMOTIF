import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ShapeValidationComponent } from './shape-validation.component';

describe('ShapeValidationComponent', () => {
  let component: ShapeValidationComponent;
  let fixture: ComponentFixture<ShapeValidationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ShapeValidationComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ShapeValidationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
