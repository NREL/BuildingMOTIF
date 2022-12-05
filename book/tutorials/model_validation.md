---
jupytext:
  cell_metadata_filter: -all
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Model Validation

The purpose of this tutorial is to walk a user through model *validation* and demonstrate how BuildingMOTIF can give useful feedback for fixing a model that has failed validation. It assumes that `BuildingMOTIF` has already been installed in the local environment.

The following are the learning objectives for this tutorial:
1. validating the model against an ***ontology*** to ensure that the model is a valid Brick model
2. validating the model against a ***manifest***, which contains the metadata requirements for a specific model
3. validating the model against a ***use case*** for a specific application

## Preliminaries and Setup

We create an in-memory BuildingMOTIF instance, create a model using the model from the previous tutoria, and load in some libraries to create the manifest with:

```{code-cell}
from rdflib import Namespace
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, Library

bm = BuildingMOTIF("sqlite://") # in-memory

# create the namespace for the building
BLDG = Namespace('urn:bldg/')

# Create the building model
model = Model.create(BLDG, description="This is a test model for a simpel building")

# load tutorial 1 model
model.graph.parse("tutorial1_model.ttl", format="ttl")

# load in some libraries
brick = Library.load(ontology_graph="../../libraries/brick/Brick-subset.ttl")
g36 = Library.load(directory="../../libraries/ashrae/guideline36")
constraints = Library.load(ontology_graph="../../buildingmotif/resources/constraints.ttl")
```

The `constraints.ttl` library we load in above is a special library with some custom constraints defined that are helpful for writing manifests.

## Validating a Model with Shapes

Validating a model is the process of ensuring that the model is both *correct* (uses the ontologies correctly) and *semantically sufficient* (it contains sufficient metadata to execute the desired applications or enable the desired use cases). Validation is always done with respect to sets of `Shapes` using the Shapes Constraint Language (SHACL)[^2].

```{note}
A `Shape` is a set of constraints, requirements and/or rules that apply to entities in an RDF graph. A shape may represent many things, including:
- the minimum points on an equipment required to execute a certain sequence of operations,
- the internal details of an equipment: what parts it contains, etc
```

BuildingMOTIF organizes `Shapes` into `Shape Collections`. The shape collection associated with a library (if there is one) can be retrieved with the `get_shape_collection` property.
Below, we use Brick's shape collection to ensure that our model is using Brick correctly:

```{code-cell}
# pass a list of shape collections to .validate()
validation_result = model.validate([brick.get_shape_collection()]) 
print(f"Model is valid? {validation_result.valid}")
```

In other tutorials, we will work with models that do **not** validate for various reasons, and explore how BuildingMOTIF helps us repair these models.

If the model was **not** valid, then we could ask the `validation_result` object to tell us why:

```python
for diff in validation_result.diffset:
    print(" -" + diff.reason())
```

## Finding Use Case Shapes

We can use a couple methods to search our libraries for shapes we might want to use. Let's start by asking the `g36` library for any system specifications it knows about, which represents *ASHRAE Guideline 36 High-Performance Sequences of Operation for HVAC Systems*[^1]. A system specification will specify all of the metadata required for an entity to run control sequences associated with that system type. 

```{code-cell}
from buildingmotif.namespaces import BMOTIF
shapes = g36.get_shape_collection()
for shape in shapes.get_shapes_of_definition_type(BMOTIF["System_Specification"]):
    print(shape)
```

## Writing Your First Manifest

A manifest is an RDF graph with a set of `Shapes` inside. These shapes place constraints and requirements on what metadata must be contained within our metadata model. For now, we will write the manifest file directly; in the future, BuildingMOTIF will contain features that make manifests easier to write.

Here is the header of our manifest file. This should also suffice for most of your own manifests:

```ttl
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix constraint: <https://nrel.gov/BuildingMOTIF/constraints#> .
@prefix : <urn:my_site_constraints/> .

: a owl:Ontology .
```

We will now add a constraint stating that our model should contain exactly 5 Brick Air Handling Units:

```ttl
:ahu-count a sh:NodeShape ;
    sh:message "Need 5 AHU" ;
    sh:targetNode : ;
    constraint:exactCount 5 ;
    constraint:class brick:AHU .
```

This basic structure can be changed to require different numbers of different Brick classes. Just don't forget to change the name of the shape (`:ahu-count`, above) when you copy-paste!

As an exercise, try writing a shape that requires the model to have exactly five Brick Supply_Fan instances and exactly five Brick CAV instances.

```{admonition} Click to reveal an answer...
:class: dropdown

```ttl
:fan-count a sh:NodeShape ;
    sh:message "Need 5 Supply Fans" ;
    sh:targetNode : ;
    constraint:exactCount 5 ;
    constraint:class brick:Supply_Fan .

:cav-count a sh:NodeShape ;
    sh:message "Need 5 CAVs" ;
    sh:targetNode : ;
    constraint:exactCount 5 ;
    constraint:class brick:CAV .
```

We can now add a shape that requires *all* AHUs in the model to match the `sz-vav-ahu` system specification we find above:

```ttl
:sz-vav-ahu-control-sequences a sh:NodeShape ;
    sh:message "AHUs must match the single-zone VAV AHU shape" ;
    sh:targetClass brick:AHU ;
    sh:node <urn:ashrae/g36/4.8/sz-vav-ahu/sz-vav-ahu> .
```

Put all of the above in a new file called `my_manifest.ttl`...

```{code-cell}
with open("my_manifest.ttl", "w") as f:
    f.write("""@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix constraint: <https://nrel.gov/BuildingMOTIF/constraints#> .
@prefix : <urn:my_site_constraints/> .

: a owl:Ontology .

:ahu-count a sh:NodeShape ;
    sh:message "Need 5 AHU" ;
    sh:targetNode : ;
    constraint:exactCount 5 ;
    constraint:class brick:AHU .

:fan-count a sh:NodeShape ;
    sh:message "Need 5 Supply Fans" ;
    sh:targetNode : ;
    constraint:exactCount 5 ;
    constraint:class brick:Supply_Fan .

:cav-count a sh:NodeShape ;
    sh:message "Need 5 CAVs" ;
    sh:targetNode : ;
    constraint:exactCount 5 ;
    constraint:class brick:CAV .

:sz-vav-ahu-control-sequences a sh:NodeShape ;
    sh:message "AHUs must match the single-zone VAV AHU shape" ;
    sh:targetClass brick:AHU ;
    sh:node <urn:ashrae/g36/4.8/sz-vav-ahu/sz-vav-ahu> .
""")
```

...and then load that manifest into BuildingMOTIF as its own library!

```{code-cell}
manifest = Library.load(ontology_graph="my_manifest.ttl")
```

## Validating our Model, Round 1

We can now ask BuildingMOTIF to validate our model against our manifest. We also have to be sure to include the supporting shape collections containing the definitions used in our manifest.

```{code-cell}
# gather these into a list for ease of use
shape_collections = [
    brick.get_shape_collection(),
    g36.get_shape_collection(),
    constraints.get_shape_collection(),
    manifest.get_shape_collection(),
]
# pass a list of shape collections to .validate()
validation_result = model.validate(shape_collections) 
print(f"Model is valid? {validation_result.valid}")
```

Our model is invalid so let's ask BuildingMOTIF for some details:

```{code-cell}
for diff in validation_result.diffset:
    print(f" - {diff.reason()}")
```

## Fixing our Model, Round 1

We are failing because we don't have the exact numbers of CAVs required by the manifest, which we forgot to add in the previous tutorial.
To fix this, use the equipment templates in the Brick library to create five CAVs and add them to the model.

Get the templates first:

```{code-cell}
from buildingmotif.namespaces import BRICK # import this to make writing URIs easier
cav_template = brick.get_template_by_name(BRICK.CAV)
```

Then check what parameters they need:

```{code-cell}
for param in cav_template.parameters:
    print(f"CAV needs '{param}'")
```

Then evaluate the templates with the chosen names of the equipment (the only parameter for the above templates) and add the resulting graphs to the model:

```{code-cell}
zone_names = ['Core_ZN', 'Perimeter_ZN_1', 'Perimeter_ZN_2', 'Perimeter_ZN_3', 'Perimeter_ZN_4']
for idx, zone_name in enumerate(zone_names):
    ahu_name = f"{zone_name}-PSZ_AC_{idx + 1}"
    cav_name = f"{ahu_name}-Diffuser"  
    bindings = {'name': BLDG[cav_name]}
    cav = cav_template.evaluate(bindings)
    model.add_graph(cav)
```

Let's check that our model contains the new entities:

```{code-cell}
print(model.graph.serialize())
```

## Validating our Model, Round 2

```{warning}
Waiting on https://github.com/RDFLib/pySHACL/pull/165 before this can be fixed...
```

We can now borrow the same code from before and re-run it to re-validate our new and improved model:

```{code-cell}
validation_result = model.validate(shape_collections) 
print(f"Model is valid? {validation_result.valid}")
print(validation_result.report_string)
```

Both AHUs fail validation because they don't match the `sz-vav-ahu` requirements. Take a look at the first bit of output which is the official SHACL validation report text format.

```{code-cell}
print("Model is invalid for these reasons:")
for diff in validation_result.diffset:
    print(f" - {diff.reason()}")
```

[^1]: https://www.ashrae.org/technical-resources/ashrae-standards-and-guidelines
[^2]: https://www.w3.org/TR/shacl/