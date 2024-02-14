# SHACL to SPARQL Conversion

BuildingMOTIF uses SHACL shapes to ensure that a metadata model contains the required metadata to support a given set of applications.
SHACL validation only yields whether or not a given node in the model passes or fails validation.
To aid in the execution of applications dependent on a SHACL shape, BuildingMOTIF provides functionality to extract from the model the nodes/edges that were used to validate the shape.

See [](../guides/generating-queries.md) for how to use the `shape_to_query` function. This page gives an overview of the algorithm.

## Shape-to-query Algorithm

The main method, `shape_to_query`, takes a SHACL shape represented as a URI and generates a SPARQL query to select information from an RDF graph that satisfies the constraints defined by the SHACL shape.
At a high level, the method works by first transforming the SHACL shape into a set of WHERE clauses, and then assembling these clauses into a complete SPARQL query.

The shape-to-query algorithm takes as input a definition of a SHACL Node Shape.

### `SELECT` clause generation

The `SELECT` clause of the resulting SPARQL query is generated as follows.
Each query has at least a `?target` variable in the generated `SELECT`  clause.
This variable represents a target node of the SHACL shape.

The algorithm adds one variable to the `SELECT` clause for each Property Shape associated
with the Node Shape through `sh:property`.
The variable name is pulled from a `sh:name` annotation on the Property Shape if one exists;
otherwise, it is assigned a generated variable name.

If a `UNION` clause exists within the SPARQL query, the algorithm generates variable names independently for each branch of the `UNION` clause.
The resulting `SELECT` clause contains the union of the different sets of variable names.

### `WHERE` clause generation

The `WHERE`  clause of the resulting SPARQL query is generated from each of the Property Shapes associated with the input Node Shape, and a few annotations directly on the NodeShape.

The Node Shape target definition is converted to a SPARQL query clause as follows:

| Target Definition | Query Pattern |
|-------------------|---------------|
| `sh:targetClass <c>` | `?target rdf:type/rdfs:subClassOf* <c>` |
| `sh:targetSubjectsOf <p>` | `?target <p> ?ignore ` |
| `sh:targetObjectsOf <p>` | `?ignore <p> ?target? ` |
| `sh:targetNode <n>` | `BIND(<n> AS ?target)` |

Additionally, any `sh:class <c>` constraint on the Node Shape is also transformed into `?target rdf:type/rdfs:subClassOf* <c>`.
Except for `sh:targetNode`, if more than one of the target clauses exists (e.g., `sh:targetClass brick:VAV, brick:RVAV`) then the algorithm uses a `UNION` clause to combine the independent query patterns.

The algorithm currently interprets a set of Property Shape-based constraint components into SPARQL query patterns.
At this stage, only the following clauses are supported:

| Property Shape pattern | SPARQL query pattern |
|------------------------|----------------------|
|`<shape> sh:property [ sh:path <path>; sh:class <class>; sh:name <name> ]` | `?target <path> ?name . ?name rdf:type/rdfs:subClassOf* <class>` |
|`<shape> sh:property [ sh:path <path>; sh:hasValue <value>]` | `?target <path> <value>` |
