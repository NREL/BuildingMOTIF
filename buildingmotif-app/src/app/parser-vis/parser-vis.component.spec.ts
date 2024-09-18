import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ParserVisComponent } from './parser-vis.component';

describe('ParserVisComponent', () => {
  let component: ParserVisComponent;
  let fixture: ComponentFixture<ParserVisComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ParserVisComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ParserVisComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
