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

# Model Creation and Validation

The purpose of this tutorial is to cover a few of the basic features of
BuildingMOTIF. To this end, the tutorial will walk the reader through building
a Brick model similar to the DOE Small Office Commercial Reference Building model.

Specifically, the tutorial has the following learning objectives:
- readers will be able to create a BuildingMOTIF "instance"
- readers will gain basic familiarity with `Libraries`, which contain `Templates` (for generating RDF models) and `Shapes` (for validating RDF models)
- readers will be able to load `Libraries` into a BuildingMOTIF instance
- readers will be able to create a Brick model by *evaluating* `Templates`
- readers will be able to use *validation* to ensure that the resulting model is a valid Brick model

The tutorial assumes that `BuildingMOTIF` has already been installed in the local environment.

## Creating a BuildingMOTIF Instance

BuildingMOTIF needs a database to store models, libraries, templates, ontologies and other pieces of data. This database can be *in-memory* (which will be deleted when the process ends) or *persistent*. For simplicity, we will start with an in-memory database where `bm` represents our BuildingMOTIF instance.

```{code-cell}
from buildingmotif import BuildingMOTIF
bm = BuildingMOTIF("sqlite://") # in-memory
```

## Creating Your First Model

Now that we have a BuildingMOTIF instance, we can create our first `Model`.

```{note}
A **Model** is an RDF graph representing a building
```

Creating a model requires importing the `Model` class, creating an RDF namespace to hold all of the entities in our model, and telling BuildingMOTIF to create a new model with that namespace. The namespace is a URL used to uniquely identify a building.

```{code-cell}
from rdflib import Namespace
from buildingmotif.dataclasses import Model

# create the namespace
BLDG = Namespace('urn:bldg/')

# Create the model! This will raise an exception if the namespace is not syntactically valid.
model = Model.create(BLDG, description="This is a test model for a simple building") 
```

We can print out the content of the model by accessing the `.graph` property of the model object. Printing this out reveals that BuildingMOTIF has added a couple annotations to the model for us, but there is otherwise no metadata about the building itself:

```{code-cell}
print(model.graph.serialize())
```

The `model.graph` object is just the RDFlib Graph that stores the model. You can interact with the graph --- e.g. by adding triples with `model.graph.add((subject, predicate, object))` --- but as we will soon see, BuildingMOTIF can automate some of that!

## Importing Libraries

Before we can add semantic building metadata to our model, we need to import some `Libraries`.

```{note}
A **Library** is a collection of Templates and Shapes. **Templates** are functions that generate parts of an RDF model. **Shapes** are functions that validate part of an RDF model.
```

We import libraries by calling `Library.load` in BuildingMOTIF. Libraries can be loaded from directories containing `.yml` and `.ttl` files (for Templates and Shapes, respectively), or from ontology files directly. The code below contains an example of importing the `brick` library, which is simply the Brick ontology. This allows BuildingMOTIF to take advantage of the classes and relationships defined by Brick when validating our model. Loading in these definitions also allows other libraries (such as ASHRAE Guideline 36) to refer to Brick definitions.

```{code-cell}
from buildingmotif.dataclasses import Library
brick = Library.load(ontology_graph="../../libraries/brick/Brick-subset.ttl")
```

One quick tip: you can ask a library for the names of the templates it defines:

```{code-cell}
print("The Brick library contains the following templates:")
for template in brick.get_templates():
    print(f"  - {template.name}")
```

## Creating a Model with Templates


### Exploring Your First Template

`Templates` make it easy to add metadata to a model without having to touch any RDF at all. Templates are functions that generate an RDF graph. This graph may represent a packaged unit like a VAV, a simple device like a Fan, a complex entity like a Chilled Water System, or anything else you may need.

The *body* of a template contains the basic structure of the graph representing that entity. Typically, a template defines several *parameters* that represent user-provided input necessary to create that entity in the model.

Let's start with the `brick` library's `HVAC Zone` template. We can fetch this out of the library by referring to it by name:

```{code-cell}
from buildingmotif.namespaces import BRICK # import this to make writing URIs easier
zone_template = brick.get_template_by_name(BRICK.HVAC_Zone)
```

We can now ask the template for the parameters it defines:

```{code-cell}
print("The Zone template has the following parameters:")
for param in zone_template.parameters:
    print(f"  {param}")
```

All templates have a mandatory `name` parameter. We can also print out the body of the template to see how those parameters will be used. Any URI that starts with a `P:` is a parameter.

```{code-cell}
print(zone_template.body.serialize())
```

### Evaluating a Template

Now that we know what the template looks like and what parameters it needs, we can *evaluate* the Template.

*Evaluation* is the process of turning a template into a graph that can be added to our model. We accomplish this with the `evaluate` function, which takes a dictionary of "bindings" as an argument. Bindings relate a parameter in the template to a value (typically a URI in your building's namespace). Put another way, the *keys* of the dictionary are the names of the parameters and the *values* of the dictionary are what will replace that parameter in the template's body.

Let's create a zone with a name of "Core_ZN", which represents the core zone of the Small Office model. We'll create the perimeter zones in the next section.

```{warning}
When creating a real Brick model, you would use BMS point names, equipment schedules, etc to determine the correct names of these entities. Other tutorials cover how to use BuildingMOTIF with these kinds of metadata sources.
```

```{code-cell}
bindings = {"name": BLDG["Core_ZN"]}
zone_entity_graph = zone_template.evaluate(bindings)
```

We can now take a look at the result of evaluating our template:

```{code-cell}
# zone_entity_graph is just an instance of rdflib.Graph
print(zone_entity_graph.serialize())
```

```{note}
For now, provide all of the parameters to the Template when evaluating. BuildingMOTIF does support partial evaluation of Templates but this is not necessary to understand or use when starting out.
```

### Adding Evaluated Templates to the Model

Now that we have an RDF graph representing a zone, let's add it to our model! Unless we add the evaluated templates to the model, the model won't know about them.

To add an RDF graph to a model, use the `add_graph` function, which we'll do for all five zones in the model.

```{code-cell}
# create a list of names for use here and for adding other entities later
zone_names = ['Core_ZN', 'Perimeter_ZN_1', 'Perimeter_ZN_2', 'Perimeter_ZN_3', 'Perimeter_ZN_4']
for name in zone_names:
    bindings = {'name': BLDG[name]}
    zone = zone_template.evaluate(bindings)
    model.add_graph(zone)

print(model.graph.serialize())
```

We can now verify that the zone has been added to the metadata model by printing the model out again:

```{code-cell}
print(model.graph.serialize())
```

```{note}
If using a persistent (disk-backed) instance of BuildingMOTIF instead of an in-memory instance, be sure to use `bm.session.commit()` to save your work after calling `add_graph`.
```

Next, we'll add a simple HVAC system of AHUs, fans, and CAV terminals to the model using the list of zone names we created above by creating a dictionary of entity names.

```{code-cell}
# create lists for names
ahu_names = []
fan_names = []
cav_names = []

# add names to lists
for idx, zone_name in enumerate(zone_names):
    ahu_name = f"{zone_name}-PSZ_AC_{idx + 1}"
    ahu_names.append(ahu_name)
    fan_names.append(f"{ahu_name}-Fan")
    cav_names.append(f"{ahu_name}-Diffuser")

# add lists to dictionary
hvac_dict = {}
hvac_dict['ahu_names'] = ahu_names
hvac_dict['fan_names'] = fan_names
hvac_dict['cav_names'] = cav_names
```

Now that we have all the entity names stored in a dictionary, we can start adding entities (evaluated templates) to the model, but first we'll need the templates.

```{code-cell}
ahu_template = brick.get_template_by_name(BRICK.AHU)
fan_template = brick.get_template_by_name(BRICK.Supply_Fan)
cav_template = brick.get_template_by_name(BRICK.CAV)
```

Let's see what parameters theses templates need.

```{code-cell}
for param in ahu_template.parameters:
    print(f"AHU needs: {param}")

for param in fan_template.parameters:
    print(f"Fan needs: {param}")

for param in cav_template.parameters:
    print(f"CAV needs: {param}")
```

We'll add the AHUs first, followed by the Fans, then the CAV terminals and print the graph after each step.

```{code-cell}
# add AHUs
for name in hvac_dict['ahu_names']:
    param_dict = {'name': BLDG[name]}
    ahu = ahu_template.evaluate(param_dict)
    model.add_graph(ahu)

print(model.graph.serialize())
```

```{code-cell}
# add AHU fans
for name in hvac_dict['fan_names']:
    param_dict = {'name': BLDG[name]}
    fan = fan_template.evaluate(param_dict)
    model.add_graph(fan)

print(model.graph.serialize())
```

```{code-cell}
# add CAVs
for name in hvac_dict['cav_names']:
    param_dict = {'name': BLDG[name]}
    cav = cav_template.evaluate(param_dict)
    model.add_graph(cav)

print(model.graph.serialize())
```

---

If you want some additional practice, try writing some Python code that adds an `Attic` zone to the model. It's unconditioned so no need to add an HVAC system to it.

```{admonition} Click to reveal an answer...
:class: dropdown

```python
bindings = {"name": BLDG["Attic"]}
zone_entity_graph = zone_template.evaluate(bindings)
model.add_graph(zone_entity_graph)
print(model.graph.serialize())
```
