import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PointlabelParserComponent } from './pointlabel-parser.component';

describe('PointlabelParserComponent', () => {
  let component: PointlabelParserComponent;
  let fixture: ComponentFixture<PointlabelParserComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PointlabelParserComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PointlabelParserComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
