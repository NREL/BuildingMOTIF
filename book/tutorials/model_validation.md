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

```{margin}
```{important}
This tutorial assumes that `BuildingMOTIF` has already been installed in the local environment.
```

The purpose of this tutorial is to learn about model *validation* and how BuildingMOTIF can give useful feedback for fixing a model that has failed validation. 

```{note}
This tutorial has the following learning objectives:
1. validating the model against an ***ontology*** to ensure that the model is a valid Brick model
2. validating the model against a ***manifest***, which contains the metadata requirements for a specific model
3. validating the model against a ***use case*** for a specific application
```

```{margin}
```{note}
 `Shapes` are functions that validate part of an RDF model. A `Shape` is a set of constraints, requirements, and/or rules that apply to entities in an RDF graph. A shape may represent many things, including:
- the minimum points on an equipment required to execute a certain sequence of operations,
- the internal details of an equipment: what parts it contains, etc
```

Validating a model is the process of ensuring that the model is both *correct* (uses the ontologies correctly) and *semantically sufficient* (it contains sufficient metadata to execute the desired applications or enable the desired use cases). Validation is always done with respect to sets of `Shapes` using the Shapes Constraint Language (SHACL)[^1].

[^1]: https://www.w3.org/TR/shacl/

## Setup

We create an in-memory BuildingMOTIF instance, load the model from the previous tutorial, and load some libraries to create the manifest with. The `constraints.ttl` library we load is a special library with some custom constraints defined that are helpful for writing manifests.

```{code-cell}
from rdflib import Namespace
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, Library
from buildingmotif.namespaces import BRICK # import this to make writing URIs easier

# in-memory instance
bm = BuildingMOTIF("sqlite://")

# create the namespace for the building
BLDG = Namespace('urn:bldg/')

# create the building model
model = Model.create(BLDG, description="This is a test model for a simple building")

# load tutorial 1 model
model.graph.parse("tutorial1_model.ttl", format="ttl")

# load in some libraries
brick = Library.load(ontology_graph="../../libraries/brick/Brick-subset.ttl")
constraints = Library.load(ontology_graph="../../buildingmotif/resources/constraints.ttl")
g36 = Library.load(directory="../../libraries/ashrae/guideline36")
```

## Model Validation - Ontology

BuildingMOTIF organizes Shapes into `Shape Collections`. The shape collection associated with a library (if there is one) can be retrieved with the `get_shape_collection` property. Below, we use Brick's shape collection to ensure that the model is using Brick correctly:

```{code-cell}
# pass a list of shape collections to .validate()
validation_result = model.validate([brick.get_shape_collection()])
print(f"Model is valid? {validation_result.valid}")
```

Success! The model is valid according to the Brick ontology.

## Model Validation - Manifest

### Writing a Manifest

```{margin}
```{note}
A `manifest` is an RDF graph with a set of `Shapes` inside, which place constraints and requirements on what metadata must be contained within a metadata model. 
```

For now, we will write a `manifest` file directly; in the future, BuildingMOTIF will contain features that make manifests easier to write. Here is the header of a manifest file. This should also suffice for most of your own manifests.

```ttl
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix constraint: <https://nrel.gov/BuildingMOTIF/constraints#> .
@prefix : <urn:my_site_constraints/> .

: a owl:Ontology .
```

We will now add a constraint stating that the model should contain exactly 1 Brick AHU.

```ttl
:ahu-count a sh:NodeShape ;
    sh:message "need 1 AHU" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:AHU .
```

This basic structure can be changed to require different numbers of different Brick classes. Just don't forget to change the name of the shape (`:ahu-count`, above) when you copy-paste!

```{attention}
As an exercise, try writing shapes that require the model to have the following.
- (1) Brick Supply_Fan
- (1) Brick Damper
- (1) Brick Cooling_Coil
- (1) Brick Heating_Coil
```

```{hint}
:class: dropdown

```ttl
:fan-count a sh:NodeShape ;
    sh:message "need 1 supply fan" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:Supply_Fan .

:damper-count a sh:NodeShape ;
    sh:message "need 1 damper" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:Damper .

:clg-coil-count a sh:NodeShape ;
    sh:message "need 1 cooling coil" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:Cooling_Coil .

:htg-coil-count a sh:NodeShape ;
    sh:message "need 1 heating coil" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:Heating_Coil .
```

<!-- We can now add a shape that requires *all* AHUs in the model to match the `sz-vav-ahu` system specification we find above:

```ttl
:sz-vav-ahu-control-sequences a sh:NodeShape ;
    sh:message "AHUs must match the single-zone VAV AHU shape" ;
    sh:targetClass brick:AHU ;
    sh:node <urn:ashrae/g36/4.8/sz-vav-ahu/sz-vav-ahu> .
``` -->

Put all of the above in a new file called `tutorial2_manifest.ttl`. We'll also add a shape called `sz-vav-ahu-control-sequences`, which is a use case shape to validate the model against in the next section.

```{code-cell}
with open("tutorial2_manifest.ttl", "w") as f:
    f.write("""
@prefix brick: <https://brickschema.org/schema/Brick#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix constraint: <https://nrel.gov/BuildingMOTIF/constraints#> .
@prefix : <urn:my_site_constraints/> .

: a owl:Ontology .

:ahu-count a sh:NodeShape ;
    sh:message "need 1 AHU" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:AHU .

:fan-count a sh:NodeShape ;
    sh:message "need 1 supply fan" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:Supply_Fan .

:damper-count a sh:NodeShape ;
    sh:message "need 1 damper" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:Damper .

:clg-coil-count a sh:NodeShape ;
    sh:message "need 1 cooling coil" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:Cooling_Coil .

:htg-coil-count a sh:NodeShape ;
    sh:message "need 1 heating coil" ;
    sh:targetNode : ;
    constraint:exactCount 1 ;
    constraint:class brick:Heating_Coil .

:sz-vav-ahu-control-sequences a sh:NodeShape ;
    sh:message "AHUs must match the single-zone VAV AHU shape" ;
    sh:targetClass brick:AHU ;
    sh:node <urn:ashrae/g36/4.8/sz-vav-ahu/sz-vav-ahu> .
""")
```

### Validating the Model

We can now ask BuildingMOTIF to validate the model against the manifest and ask BuildingMOTIF for some details if it fails. We also have to be sure to include the supporting shape collections containing the definitions used in the manifest.

```{code-cell}
# load manifest into BuildingMOTIF as its own library!
manifest = Library.load(ontology_graph="tutorial2_manifest.ttl")

# gather shape collections into a list for ease of use
shape_collections = [
    brick.get_shape_collection(),
    constraints.get_shape_collection(),
    manifest.get_shape_collection(),
    g36.get_shape_collection(),
]

# pass a list of shape collections to .validate()
validation_result = model.validate(shape_collections)
print(f"Model is valid? {validation_result.valid}")

# print reasons
for diff in validation_result.diffset:
    print(f" - {diff.reason()}")
```

### Fixing the Model

The model is failing because we don't have a heating coil required by the manifest, which we forgot to add in the previous tutorial. It's also failing the use case validation, which we'll cover in the next section. To fix the manifest validation, use the equipment templates in the Brick library to create a heating coil, add it to the model, and connect it to the AHU using RDFLib's `graph.add()` method.

```{code-cell}
# ahu name
ahu_name = "Core_ZN-PSC_AC"

# get template
htg_coil_template = brick.get_template_by_name(BRICK.Heating_Coil)

# add htg coil
htg_coil_name = f"{ahu_name}-Htg_Coil"
htg_coil_binding = {"name": BLDG[htg_coil_name]}
htg_coil_graph = htg_coil_template.evaluate(htg_coil_binding)
model.add_graph(htg_coil_graph)

# connect htg coil
model.graph.add((BLDG[ahu_name], BRICK.hasPart, BLDG[htg_coil_name]))

# print model to confirm component was added and connected
print(model.graph.serialize())
```

We can see that the heating coil was added to the model and connected to the AHU so let's check if the manifest validation failure was fixed.

```{code-cell}
# pass a list of shape collections to .validate()
validation_result = model.validate(shape_collections)
print(f"Model is valid? {validation_result.valid}")

# print reasons
for diff in validation_result.diffset:
    print(f" - {diff.reason()}")
```

Success! The model is no longer failing the manifest validation.

## Model Validation - Use Case 

### Finding Use Case Shapes

We can use a couple methods to search the libraries for shapes we might want to use. Let's start by asking the `g36` library for any system specifications it knows about. This library represents *ASHRAE Guideline 36 High-Performance Sequences of Operation for HVAC Systems*[^2]. A system specification will specify all of the metadata required for an entity to run control sequences associated with that system type.

[^2]: https://www.ashrae.org/technical-resources/ashrae-standards-and-guidelines

```{code-cell}
from buildingmotif.namespaces import BMOTIF
shapes = g36.get_shape_collection()
for shape in shapes.get_shapes_of_definition_type(BMOTIF["System_Specification"]):
    print(shape)
```

The model represents the Small Office Commercial Prototype Building model, which has single zone packaged AHUs, so we're interested in validating it against Section 4.8 of Guideline 36 for single zone variable air volume (VAV) AHUs. 

<!-- Let's append a reference to that shape in the manifest file.
```{code-cell}
with open("tutorial2_manifest.ttl", "a") as f:
    f.write("""
:sz-vav-ahu-control-sequences a sh:NodeShape ;
    sh:message "AHUs must match the single-zone VAV AHU shape" ;
    sh:targetClass brick:AHU ;
    sh:node <urn:ashrae/g36/4.8/sz-vav-ahu/sz-vav-ahu> .
""")
``` -->

### Validating the Model

<!-- We can now borrow the same code from before and re-run it to re-validate the model:

```{code-cell}
# load manifest into BuildingMOTIF as its own library!
manifest = Library.load(ontology_graph="tutorial2_manifest.ttl")

# gather these into a list for ease of use
shape_collections = [
    brick.get_shape_collection(),
    constraints.get_shape_collection(),
    manifest.get_shape_collection(),
    g36.get_shape_collection(),
]

# pass a list of shape collections to .validate()
validation_result = model.validate(shape_collections)
print(f"Model is valid? {validation_result.valid}")
``` -->
As shown in the previous section, the AHU fails validation because it doesn't match the `sz-vav-ahu-control-sequences` requirements. Take a look at the first bit of output, which is the official SHACL validation report text format. These aren't very understandable but BuildingMOTIF can make this output more interpretable!

```{code-cell}
# SHACL validation report
print(validation_result.report_string)

# separator
print("-"*79)

# BuildingMOTIF output
print("Model is invalid for these reasons:")
for diff in validation_result.diffset:
    print(f" - {diff.reason()}")
```

The model is failing because the AHU doesn't have the minimum number of supply fans associated with it. We *could* add the fan explicitly by adding those triples to the model like we've done previously, but we can also ask BuildingMOTIF to generate new templates that explicitly prompt us for the missing information. We'll cover this feature in the next tutorial so let's save the model.

```{code-cell}
#save model
model.graph.serialize(destination="tutorial2_model.ttl")
```
