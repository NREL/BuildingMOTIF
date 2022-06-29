Developer FAQ
=============

This page documents design decisions or recurring development-oriented questions about BuildingMOTIF

**What is the relationship between templates, shapes and ontologies?**

Templates and shapes generate and validate parts of a model, respectively.
They may be defined in several different ways; so far, there are 2:

* **Ontologies / RDF graphs** can contain SHACL shapes (instances of `sh:NodeShape`) and templates. Templates are not specific RDF constructs --- i.e. there is no ontology/schema that defines the template --- but are instead *inferred* from SHACL shapes. When an ontology file is loaded into a BuildingMOTIF instance, BuildingMOTIF will extract all of the SHACL shapes and generate templates from them. BuildingMOTIF will generate templates for all entities in an RDF graph that are instances of *both* `sh:NodeShape` and `owl:Class`.
* **YAML files** can contain templates specified in a syntactic sugar
