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

# Use Case Validation

The purpose of this tutorial is to walk a user through creating a `Manifest` which contains the metadata requirements for a given model. Specifically, the user will create a manifest for a simple HVAC system containing one AHU and two VAVs, where the two VAVs each implement a control sequence from ASHRAE Guideline 36. The tutorial will also demonstrate how BuildingMOTIF can validate a model against the manifest and then give useful feedback for fixing up the model.

The tutorial assumes that `BuildingMOTIF` has already been installed in the local environment.

The tutorial also assumes that the reader has some familiarity with the Turtle serialization format for RDF graphs.

## Preliminaries and Setup

We create an in-memory BuildingMOTIF instance and load in some libraries to create the manifest with:

```{code-cell}
from rdflib import Namespace
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, Library

bm = BuildingMOTIF("sqlite://") # in-memory

# create the namespace for the building
BLDG = Namespace('urn:bldg/')

# Create the building model
model = Model.create(BLDG, description="This is a test model for a simpel building")

# load in some libraries
brick = Library.load(ontology_graph="../../libraries/brick/Brick-subset.ttl")
g36 = Library.load(directory="../../libraries/ashrae/guideline36")
constraints = Library.load(ontology_graph="../../buildingmotif/resources/constraints.ttl")
```

The `constraints.ttl` library we load in above is a special library with some custom constraints defined that are helpful for writing manifests.

## Finding Use Case Shapes

We can use a couple methods to search our libraries for shapes we might want to use. Let's start by asking the `g36` library for any system specifications it knows about; a system specification will specify all of the metadata required for an entity to run control sequences associated with that system type.

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

We will now add a constraint stating that our model should contain exactly 1 Brick Air Handling Unit:

```ttl
:ahu-count a sh:NodeShape ;
    sh:message "Need 1 AHU" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:AHU .
```

This basic structure can be changed to require different numbers of different Brick classes. Just don't forget to change the name of the shape (`:ahu-count`, above) when you copy-paste!

As an exercise, try writing a shape that requires the model to have exactly two Brick VAV instances.
```{admonition} Click to reveal an answer...
:class: dropdown

```ttl
:vav-count a sh:NodeShape ;
    sh:message "Need 2 VAVs" ;
    sh:targetNode : ;
    constraint:exactCount 2 ;
    constraint:class brick:VAV .
```

We can now add a shape that requires *all* VAVs in the model to match the `vav-cooling-only` system specification we find above:

```ttl
:vav-control-sequences a sh:NodeShape ;
    sh:message "VAVs must match the cooling only shape" ;
    sh:targetClass brick:VAV ;
    sh:node <urn:ashrae/g36/4.1/vav-cooling-only/vav-cooling-only> .
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
    sh:message "Need 1 AHU" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:AHU .

:vav-count a sh:NodeShape ;
    sh:message "Need 2 VAVs" ;
    sh:targetNode : ;
    constraint:exactCount 2 ;
    constraint:class brick:VAV .

:vav-control-sequences a sh:NodeShape ;
    sh:message "VAVs must match the cooling only shape" ;
    sh:targetClass brick:VAV ;
    sh:node <urn:ashrae/g36/4.1/vav-cooling-only/vav-cooling-only> .
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

To no big surprise, our empty model is indeed invalid. Let's ask BuildingMOTIF for some details:

```{code-cell}
for diff in validation_result.diffset:
    print(f" - {diff.reason()}")
```

## Fixing our Model, Round 1

We are failing because we don't have the exact numbers of VAVs and AHUs required by the manifest.
To fix this, use the equipment templates in the Brick library to create 2 VAVs and 1 AHU and add them to the model.

Get the templates first:

```{code-cell}
from buildingmotif.namespaces import BRICK # import this to make writing URIs easier
vav_template = brick.get_template_by_name(BRICK.VAV)
ahu_template = brick.get_template_by_name(BRICK.AHU)
```

Then check what parameters they need

```{code-cell}
for param in vav_template.parameters:
    print(f"VAV needs '{param}'")
for param in ahu_template.parameters:
    print(f"AHU needs '{param}'")
```

Then evaluate the templates with the chosen names of the equipment (the only parameter for the above templates) and add the resulting graphs to the model:

```{code-cell}
vav1 = vav_template.evaluate({"name": BLDG["vav1"]})
model.add_graph(vav1)
vav2 = vav_template.evaluate({"name": BLDG["vav2"]})
model.add_graph(vav2)
ahuA = ahu_template.evaluate({"name": BLDG["ahuA"]})
model.add_graph(ahuA)
```

Let's check that our model contains the new entities:

```{code-cell}
print(model.graph.serialize())
```

## Validating our Model, Round 2

We can now borrow the same code from before and re-run it to re-validate our new and improved model:

```{code-cell}
validation_result = model.validate(shape_collections) 
print(f"Model is valid? {validation_result.valid}")
for diff in validation_result.diffset:
    print(f" - {diff.reason()}")
```
