export interface Template {
    name: string;
    id: number;
    body_id: number;
    optional_args: string[];
    library_id: string;
    dependency_ids: number[];
  }
  