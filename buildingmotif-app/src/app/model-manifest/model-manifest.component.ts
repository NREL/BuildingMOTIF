import { Component, Input, OnInit } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { LibraryService, Library } from '../library/library.service';
import { Template } from '../types';
import { ModelDetailService } from '../model-detail/model-detail.service';

@Component({
  selector: 'app-model-manifest',
  templateUrl: './model-manifest.component.html',
  styleUrls: ['./model-manifest.component.css'],
  providers: [LibraryService, ModelDetailService]
})
export class ModelManifestComponent implements OnInit {
  @Input() modelId!: number;

  libraries: Library[] = [];
  selectedLibrariesForm: FormGroup = new FormGroup({});
  selectedTemplatesForm: FormGroup = new FormGroup({});
  templates: Template[] = [];

  loadingLibraries = false;
  loadingTemplates = false;
  saving = false;

  constructor(
    private libraryService: LibraryService,
    private modelDetailService: ModelDetailService
  ) {}

  ngOnInit(): void {
    this.loadingLibraries = true;
    this.libraryService.getAllLibraries().subscribe({
      next: (libs: Library[]) => {
        this.libraries = libs;
        const controls: { [key: string]: FormControl } = {};
        this.libraries.forEach(l => controls[l.id] = new FormControl(false));
        this.selectedLibrariesForm = new FormGroup(controls);

        this.modelDetailService.getManifestLibraryImports(this.modelId).subscribe({
          next: (res: { library_ids: number[] }) => {
            res.library_ids.forEach(id => this.selectedLibrariesForm.get(String(id))?.setValue(true, { emitEvent: false }));
            this.refreshTemplates();
          },
          error: () => { this.refreshTemplates(); }
        });
      },
      complete: () => { this.loadingLibraries = false; }
    });

    this.selectedLibrariesForm.valueChanges.subscribe(() => this.refreshTemplates());
  }

  private getSelectedLibraryIds(): number[] {
    return Object.keys(this.selectedLibrariesForm.controls)
      .filter(k => this.selectedLibrariesForm.get(k)?.value)
      .map(k => parseInt(k, 10));
  }

  private refreshTemplates(): void {
    const selectedLibIds = this.getSelectedLibraryIds();
    if (selectedLibIds.length === 0) {
      this.templates = [];
      this.selectedTemplatesForm = new FormGroup({});
      return;
    }
    this.loadingTemplates = true;
    forkJoin(selectedLibIds.map(id => this.libraryService.getLibrarysTemplates(id))).subscribe({
      next: (libsWithTemplates: any[]) => {
        const templates = libsWithTemplates.flatMap(l => l.templates || []);
        const byId: { [id: number]: Template } = {};
        templates.forEach((t: any) => { if (t?.id !== undefined) byId[t.id] = t; });
        this.templates = Object.values(byId);

        const tControls: { [key: string]: FormControl } = {};
        this.templates.forEach((t: any) => tControls[t.id] = new FormControl(false));
        this.selectedTemplatesForm = new FormGroup(tControls);
      },
      complete: () => { this.loadingTemplates = false; }
    });
  }

  saveManifest(): void {
    const library_ids = this.getSelectedLibraryIds();
    const selected_template_ids = Object.keys(this.selectedTemplatesForm.controls)
      .filter(k => this.selectedTemplatesForm.get(k)?.value)
      .map(k => parseInt(k, 10));

    this.saving = true;
    this.modelDetailService.saveManifest(this.modelId, library_ids, selected_template_ids)
      .subscribe({
        complete: () => { this.saving = false; }
      });
  }
}
