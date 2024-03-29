export interface Template {
    name: string;
    id: number;
    body_id: number;
    optional_args: string[];
    library_id: string;
    dependency_ids: number[];
    parameters?: string[];
}

export interface Model {
  name: string;
  id: number;
  graph_id: number;
  description: string;
}
