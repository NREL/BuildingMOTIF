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

# Quick Tutorial

The purpose of this tutorial is to cover a few of the basic features of BuildingMOTIF. To this end, the tutorial will walk the reader through building a Brick model for a simple HVAC system. The resulting Brick model will contain sufficient metadata to execute a couple fault detection rules defined by ASHRAE Guideline 36.

Specifically, the tutorial has the following learning objectives:
- readers will be able to create a BuildingMOTIF "instance"
- readers will gain basic familiarity with `Libraries`, which contain `Templates` (for generating RDF models) and `Shapes` (for validating RDF models)
- readers will be able to load `Libraries` into a BuildingMOTIF instance
- readers will be able to create a Brick model by *evaluating* `Templates`
- readers will be able to use *validation* to ensure that the resulting model is a valid Brick model
- readers will be able to use BuildingMOTIF to discover which fault detection rules can run on the resulting Brick model

The tutorial assumes that `BuildingMOTIF` has already been installed in the local environment.

## Creating a BuildingMOTIF Instance

BuildingMOTIF needs a database to store models, libraries, templates, ontologies and other pieces of data. This database can be *persistent* or *in-memory* (which will be deleted when the process ends). For simplicity, we will start with an in-memory database.

```{code-cell}
from buildingmotif import BuildingMOTIF
bm = BuildingMOTIF("sqlite://") # in-memory
```

`bm` represents our BuildingMOTIF instance.

## Creating Your First Model

Now that we have a BuildingMOTIF instance, we can create our first `Model`.

```{note}
A **Model** is an RDF graph representing a building
```

Creating a model requires importing the `Model` class, creating an RDF namespace to hold all of the entities in our model, and telling BuildingMOTIF to create a new model with that namespace. The namespace is a URL used to uniquely identify a building.

```{code-cell}
from buildingmotif.dataclasses import Model
from rdflib import Namespace

# create the namespace
BLDG = Namespace('urn:bldg/')

# Create the model!
model = Model.create(BLDG, description="This is a test model for a simpel building")

# This will raise an exception if the namespace
# is not syntactically valid
```

We can print out the content of the model by accessing the `.graph` property of the model object. Printing this out reveals that BuildingMOTIF has added a couple annotations to the model for us, but there is otherwise no metadata about the building itself:

```{code-cell}
print(model.graph.serialize())
```

The `model.graph` object is just the RDFlib Graph that stores the model. You can interact with the graph --- e.g. by adding triples with `model.graph.add((subject, predicate, object))` --- but as we will soon see, BuildingMOTIF can automate some of that!

## Importing Libraries

Before we can add semantic building metadata to our model, we need to import some `Libraries`.

```{note}
A **Library** is a collection of Templates and Shapes. **Templates** are functions that generate parts of an RDF model. **Shapes** are functions which validate part of an RDF model
```

We import libraries by calling `Library.load` in BuildingMOTIF. Libraries can be loaded from directories containing `.ttl` and `.yml` files (for shapes and templates, respectively), or from ontology files directly. The code below contains an example of each of these.

```{code-cell}
from buildingmotif.dataclasses import Library
brick = Library.load(ontology_graph="../../libraries/brick/Brick-subset.ttl")
g36 = Library.load(directory="../../libraries/ashrae/guideline36")
```

The `brick` library is simply the Brick ontology. This allows BuildingMOTIF to take advantage of the classes and relationships defined by Brick when validating our model. Loading in these definitions also allows other libraries (like `g36` below) to refer to Brick definitions.

The `g36` library is a set of templates representing the system configurations defined in the Guideline 36 document. We will use these templates later to create part of our Brick model. The `g36` library also contains a number of `Shapes` representing the metadata requirements for a few fault detection rules --- we will also revisit these.

One quick tip: you can ask a library for the names of the templates it defines:

```{code-cell}
print("The G36 library contains the following templates:")
for template in g36.get_templates():
    print(f"  - {template.name}")
```

## Creating a Model by Evaluating Templates


### Exploring Your First Template

`Templates` make it easy to add metadata to a model without having to touch any RDF at all. Templates are functions which generate an RDF graph. This graph may represent a packaged unit like a VAV, a simple device like a Fan, a complex entity like a Chilled Water System, or anything else you may need.

The *body* of a template contains the basic structure of the graph representing that entity. Typically, a template defines several *parameters* which represent user-provided input necessary to create that entity in the model.

Let's start with the `g36` library's `fan` template. We can fetch this out of the library by referring to it by name:

```{code-cell}
fan_template = g36.get_template_by_name("fan")
```

We can now ask the template for which parameters it defines:

```{code-cell}
print("The fan template has the following parameters:")
for param in fan_template.parameters:
    print(f"  {param}")
```

All parameters have a mandatory `name` parameter. This template also defines three other parameters: 
- `speed`: a point holding the current speed of the fan
- `start_stop`: a command point to start or stop the fan
- `status`: the current fan status

We can also print out the body of the template to see how those parameters will be used:

```{code-cell}
print(fan_template.body.serialize())
```

Any URI that starts with a `P:` is a parameter.

Finally, we can ask whether there the template has any *dependencies*. A dependency is how a template refers to another template. A dependency is also how you can determine what kind of value is exepcted for a given parameter.

```{code-cell}
print("The fan template has the following dependencies:")
for dependency in fan_template.get_dependencies():
    print(f"  {dependency.template.name}")
    for (theirs, ours) in dependency.args.items():
        print(f"  {dependency.template.name}'s {theirs} parameter corresponds to fan_template's {ours} parameter")
    print(f"  {dependency.template.name}")
```

### Evaluating a Template

Now that we know what the template looks like and what parameters it needs, we can *evaluate* the Template.

*Evaluation* is the process of turning a template into a graph that can be added to our model. We accomplish this with the `evaluate` function, which takes a dictionary of "bindings" as an argument. Bindings relate a parameter in the template to a value (typically a URI in your building's namespace). Put another way, the *keys* of the dictionary are the names of the parameters and the *values* of the dictionary are what will replace that parameter in the template's body.

Let's create a fan with a name of "fan123" and use some obvious-sounding names for the rest of the points. 

```{warning}
When creating a real Brick model, you would use BMS point names, equipment schedules, etc to determine the correct names of these entities. Other tutorials cover how to use BuildingMOTIF with these kinds of metadata sources.
```

```{code-cell}
bindings = {
    "name": BLDG["fan123"],
    "speed": BLDG["fan123-speed"],
    "start_stop": BLDG["fan123-start-stop"],
    "status": BLDG["fan123-status"],
}
fan_entity_graph = fan_template.evaluate(bindings)
```

We can now take a look at the result of evaluating our template:

```{code-cell}
# fan_entity_graph is just an instance of rdflib.Graph
print(fan_entity_graph.serialize())
```

```{note}
For now, provide all of the parameters to the Template when evaluating. BuildingMOTIF does support partial evaluation of Templates but this is not necessary to understand or use when starting out.
```

### Adding an Evaluated Template to the Model

Now that we have an RDF graph representing the fan, let's add it to our model! Unless we add the evaluated templates to the model, the model won't know about them.

To add an RDF graph to a model, use the `add_graph` function:

```{code-cell}
model.add_graph(fan_entity_graph)
```

We can now verify that the fan has been added to the metadata model by printing the model out again:

```{code-cell}
print(model.graph.serialize())
```

```{note}
If using a persistent (disk-backed) instnace of BuildingMOTIF instead of an in-memory instance, be sure to use `bm.session.commit()` to save your work after calling `add_graph`.
```
