# BuildingMOTIF API Reference

This document describes the HTTP API endpoints implemented in this repository, with enough detail for an AI agent (or frontend developer) to call them correctly.

Conventions:
- All paths are relative to the API base URL.
- Unless otherwise stated, responses are JSON and UTF-8 encoded.
- Errors use: { "message": string } with appropriate HTTP status codes (e.g., 400 Bad Request, 404 Not Found, 500 Internal Server Error).
- IDs are integers; URIs are strings.
- When posting Turtle (TTL) content, set header: Content-Type: text/turtle.
- Some endpoints use content negotiation (Accept header) to choose between JSON and text/turtle.

---

## Libraries

### GET /libraries
Return all libraries.

- Response 200 JSON: array of library objects (serializer-defined).
  - Includes at least: id (number), name (string), shape_collection (object with id), possibly template IDs.
- Errors: none.

Example:
- GET /libraries

---

### GET /libraries/shapes
Return shapes grouped by BuildingMOTIF definition type.

- Response 200 JSON: object keyed by definition type URI, each a list of:
  - { shape_uri: string, label: string|null, library_name: string, shape_collection_id: number }

Example:
- GET /libraries/shapes

---

### GET /libraries/{library_id}
Return a single library by ID.

- Path params:
  - library_id: number
- Response 200 JSON: library object (serializer-defined)
- Errors:
  - 404: { "message": "ID: {library_id}" }

Example:
- GET /libraries/1

---

### GET /libraries/{library_id}/classes
List classes in the library’s shape collection. Optionally filter by subclasses of a given class.

- Path params:
  - library_id: number
- Query params:
  - subclasses_of: URI-encoded class URI (optional)
- Response 200 JSON: array of { uri: string, label: string|null, definition: string|null }
- Errors:
  - 404 if library not found
  - 500 on query/processing errors

Example:
- GET /libraries/1/classes
- GET /libraries/1/classes?subclasses_of=http%3A%2F%2Fexample.org%2FMyClass

---

### GET /libraries/{library_id}/shape_collection/ontology_name
Return the ontology name (graph_name) of the library’s shape collection.

- Path params:
  - library_id: number
- Response 200 JSON: { ontology_name: string|null }
- Errors:
  - 404: { "message": "ID: {library_id}" }

Example:
- GET /libraries/1/shape_collection/ontology_name

---

## Templates

### GET /templates
Return all templates.

- Response 200 JSON: array of template objects (serializer-defined)

Example:
- GET /templates

---

### GET /templates/{template_id}
Return a single template by ID.

- Path params:
  - template_id: number
- Query params:
  - parameters: boolean (optional; include parameter details)
- Response 200 JSON: template object (serializer-defined)
- Errors:
  - 404: { "message": "ID: {template_id}" }

Example:
- GET /templates/10
- GET /templates/10?parameters=true

---

### POST /templates/{template_id}/evaluate/ingress
Evaluate a template using CSV ingress against a specific model.

- Path params:
  - template_id: number
- Query params:
  - model_id: number (required)
- Headers:
  - Content-Type: text/plain or application/octet-stream (raw CSV bytes)
- Body: CSV content (raw bytes)
- Response 200 body: text/turtle (TTL graph of evaluation result)
- Errors:
  - 404 for missing template or model
  - 400 for missing file or invalid CSV

Example:
- POST /templates/10/evaluate/ingress?model_id=5
  - Body: CSV file bytes

---

### POST /templates/{template_id}/evaluate/bindings
Evaluate a template by providing explicit bindings.

- Path params:
  - template_id: number
- Headers:
  - Content-Type: application/json
- Body JSON:
  - {
      "model_id": number,
      "bindings": {
        "<paramName>": { "@id": "uri" } | { "@literal": "value", "@datatype"?: "uri" }
      }
    }
- Response 200 body: text/turtle (TTL graph)
- Errors:
  - 404 for missing template or model
  - 400 for wrong content-type, missing model_id, missing bindings, or invalid payload

Example body:
{
  "model_id": 5,
  "bindings": {
    "point": { "@id": "urn:example:Point1" },
    "label": { "@literal": "Zone Temp", "@datatype": "http://www.w3.org/2001/XMLSchema#string" }
  }
}

---

### GET /templates/{template_id}/body
Return the raw template body (graph) as TTL.

- Path params:
  - template_id: number
- Response 200 body: text/turtle
- Errors:
  - 404: { "message": "ID: {template_id}" }

Example:
- GET /templates/10/body

---

## Parsers

### POST /parsers
Parse an array of point labels with a supplied parser configuration.

- Headers:
  - Content-Type: application/json
- Body JSON:
  - { "parsers": <parser-config>, "point_labels": string[] }
- Response 200 JSON: array of parsed results (one per point label)

Example body:
{
  "parsers": { ... },
  "point_labels": ["ZN-T", "ZN-RH"]
}

---

## Graphs

### GET /graph/{graph_id}
Return an RDF graph by its identifier.

- Path params:
  - graph_id: string — the graph identifier (typically a URI); must be URL-encoded in the path
- Content negotiation:
  - If the request includes Content-Type or Accept headers, the server uses them to choose a serialization:
    - text/turtle → Turtle (default)
    - application/ld+json or application/json → JSON-LD
    - application/rdf+xml → RDF/XML
    - application/n-triples or text/plain → N-Triples
    - text/n3 → Notation3
    - application/n-quads → N-Quads
    - application/trig → TriG
  - If multiple media types are provided, the first one is used; parameters are ignored.
- Response 200 body: the graph serialized in the negotiated format
- Errors:
  - 404: { "message": "ID: {graph_id}" } when the named graph is not found or is empty

Examples:
- GET /graph/urn%3Amy%3Agraph%3Aid            (defaults to text/turtle)
- GET /graph/urn%3Amy%3Agraph%3Aid  (Content-Type: application/ld+json)
- GET /graph/urn%3Amy%3Agraph%3Aid  (Accept: application/rdf+xml)

---

## Models

### GET /models
Return all models.

- Response 200 JSON: array of model objects (serializer-defined)

Example:
- GET /models

---

### POST /models
Create a model.

- Headers:
  - Content-Type: application/json
- Body JSON:
  - { "name": string, "description"?: string }
  - name should be a URI (e.g., "urn:building:Model1")
- Response:
  - 201 JSON: created model (serializer-defined)
  - 400 for missing name, invalid name, or wrong content-type

Example body:
{ "name": "urn:example:model1", "description": "My model" }

---

### GET /models/{model_id}
Return a single model by ID.

- Path params:
  - model_id: number
- Response 200 JSON: model object (serializer-defined)
- Errors:
  - 404: { "message": "ID: {model_id}" }

Example:
- GET /models/5

---

### GET /models/{model_id}/graph
Return the model graph as TTL.

- Path params:
  - model_id: number
- Response 200 body: text/turtle
- Errors:
  - 404: { "message": "ID: {model_id}" }

Example:
- GET /models/5/graph

---

### PATCH /models/{model_id}/graph
Append triples to the model graph.

- Path params:
  - model_id: number
- Headers:
  - Content-Type: application/xml  (note: body is Turtle, header retained for compatibility)
- Body: Turtle text
- Response 200 body: text/turtle (updated model graph)
- Errors:
  - 400 for wrong content-type or invalid TTL
  - 404 for missing model

Example:
- PATCH /models/5/graph

---

### PUT /models/{model_id}/graph
Overwrite the model graph.

- Same request shape as PATCH, but replaces the entire graph instead of appending.

Example:
- PUT /models/5/graph

---

### GET /models/{model_id}/node_subgraph
Return the Concise Bounded Description (CBD) of a node within the model graph.

- Path params:
  - model_id: number
- Query params:
  - node: URI (required) — the node to describe
  - self_contained: boolean (optional; default true) — when true, iteratively expands the CBD by including CBDs of discovered nodes until convergence
- Response 200 body: text/turtle (TTL graph of the CBD)
- Errors:
  - 400 for missing/invalid query params
  - 404 for missing model

Example:
- GET /models/5/node_subgraph?node=urn%3Aexample%3Asubject
- GET /models/5/node_subgraph?node=urn%3Aexample%3Asubject&self_contained=false

### GET /models/{model_id}/target_nodes
Return a list of target node types found in the model graph.

- Path params:
  - model_id: number
- Response 200 JSON: array of distinct rdf:type values (strings)
- Errors:
  - 404: { "message": "ID: {model_id}" }

Example:
- GET /models/5/target_nodes

---

## Model Manifest (primary)

### GET /models/{model_id}/manifest
Return the current manifest.

- Path params:
  - model_id: number
- Accept:
  - application/json → 200 JSON: { "body": string, "library_uris": string[] }
    - body: Turtle string of the manifest graph
    - library_uris: objects of owl:imports in the manifest
  - Otherwise → 200 body: text/turtle
- Errors:
  - 404: { "message": "ID: {model_id}" }

Examples:
- GET /models/5/manifest (Accept: application/json)
- GET /models/5/manifest (Accept: text/turtle)

---

### POST /models/{model_id}/manifest
Replace/update the manifest. Two modes:

1) JSON mode
- Headers:
  - Content-Type: application/json
- Body JSON (either or both):
  - { "library_ids"?: number[], "library_uris"?: string[] }
- Behavior:
  - Resolves library_ids to their shape collection graph_name (URI).
  - Merges resolved URIs and library_uris (deduplicated, preserving order).
  - Replaces the manifest with a minimal graph that contains owl:imports pointing to those URIs.
- Response 200 body: text/turtle (updated manifest)
- Errors:
  - 400 for invalid types or unknown library IDs
  - 404 for missing model

2) Turtle mode
- Headers:
  - Content-Type: text/turtle
- Body: Turtle graph text
- Behavior:
  - Replaces the entire manifest graph with the posted graph.
- Response 200 body: text/turtle (normalized manifest)
- Errors:
  - 400 for invalid TTL
  - 404 for missing model

Examples:
- POST /models/5/manifest with JSON { "library_ids": [1,2] }
- POST /models/5/manifest with JSON { "library_uris": ["urn:lib:a","urn:lib:b"] }
- POST /models/5/manifest with TTL body

---

## Model Manifest Imports (auxiliary)

### GET /models/{model_id}/manifest/imports
Return library IDs parsed from owl:imports that match the prefix:
https://nrel.gov/BuildingMOTIF/library/{id}

- Response 200 JSON: { "library_ids": number[] }

---

### POST /models/{model_id}/manifest/imports
Replace owl:imports using the fixed prefix above.

- Headers:
  - Content-Type: application/json
- Body JSON:
  - { "library_ids": number[], "selected_template_ids"?: number[] }
- Response 200 JSON: echoes { library_ids, selected_template_ids }
- Notes:
  - This endpoint is legacy/helper; prefer the primary manifest endpoint.

---

## Validation

### POST /models/{model_id}/validate
Validate the model using SHACL shapes.

- Path params:
  - model_id: number
- Query params:
  - shacl_engine: string (optional)
  - min_iterations: integer (optional; minimum 1; default 1)
  - max_iterations: integer (optional; minimum 1; default 3)
- Content:
  - No/empty body → validates against the model’s manifest
  - JSON body:
    - Headers: Content-Type: application/json
    - Body JSON: { "library_ids"?: number[] }
      - 0 means “use the model’s manifest”; other IDs load corresponding libraries’ shape collections
- Response 200 JSON:
  - {
      "message": string,   // validation report string
      "valid": boolean,
      "reasons": { [focus_node_uri: string]: string[] }
    }
- Errors:
  - 400 for invalid library IDs
  - 400 for invalid min_iterations/max_iterations
  - 404 for missing model

Example:
- POST /models/5/validate
- POST /models/5/validate with JSON { "library_ids": [0, 1, 2] }

---

### POST /models/{model_id}/validate_shape
Validate the model against specific shapes.

- Query params:
  - min_iterations: integer (optional; minimum 1; default 1)
  - max_iterations: integer (optional; minimum 1; default 3)
- Headers:
  - Content-Type: application/json
- Body JSON:
  - {
      "shape_collection_ids": number[],
      "shape_uris": string[],
      "target_class": string
    }
- Response 200 JSON: { [shape_uri: string]: string[] } // reasons per tested shape
- Errors:
  - 400 for missing/invalid parameters
  - 404 for missing model

Example body:
{
  "shape_collection_ids": [3],
  "shape_uris": ["urn:shape:ExampleShape"],
  "target_class": "urn:brick:MyClass"
}

---

## FDD Rules → Manifest

### POST /models/{model_id}/add_manifest_rules
Add FDD rules to the model’s manifest.

- Headers:
  - Content-Type: application/json
- Body JSON: rules JSON (schema depends on rule generator)
- Response 200 JSON:
  - {
      "grouped_diffs": ...,
      "successful_rules": ...,
      "validation_report": "<ttl string>"
    }
- Errors:
  - 400 invalid JSON body
  - 404 missing model

---

## Notes and Tips

- Graph retrieval: GET /graph/{graph_id} uses Content-Type or Accept to negotiate the RDF serialization; defaults to text/turtle.
- Model graph updates: For PATCH/PUT /models/{model_id}/graph, send Turtle in the body but keep Content-Type: application/xml (compatibility header).
- Manifest endpoint supports content negotiation on GET (JSON vs Turtle).
- Ontology name (graph_name) for a library’s shape collection is available at:
  - GET /libraries/{library_id}/shape_collection/ontology_name
- When posting JSON to manifest, prefer library_ids to avoid hardcoding URIs; the API resolves them to the proper graph_name URIs.
