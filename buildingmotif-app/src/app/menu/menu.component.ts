import { Component, OnInit } from '@angular/core';
import { Router, ActivatedRoute, ParamMap } from '@angular/router';
import { TemplateSearchComponent } from '../template-search/template-search.component'

interface NavItem {
  title: string;
  route: string;
}

@Component({
  selector: 'app-menu',
  templateUrl: './menu.component.html',
  styleUrls: ['./menu.component.css']
})
export class MenuComponent {
  readonly navItems: NavItem[];

  constructor(
    private route: ActivatedRoute,
  ) {
    this.navItems = [
      {
        title: 'Templates',
        route: '/templates',
      }, {
        title: 'Models',
        route: '/models',
      }
    ]
  }
}
