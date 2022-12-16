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

# Model Creation

```{margin}
```{important}
This tutorial assumes that `BuildingMOTIF` has already been installed in the local environment.
```

The purpose of this tutorial is to learn about a few of the basic features of BuildingMOTIF by creating a Brick model similar to the Small Office Commercial Prototype Building model[^1]. It assumes that the reader has some familiarity with the Turtle syntax[^2] for Resource Description Framework (RDF) graphs[^3].

```{note}
This tutorial has the following learning objectives:
1. creating a BuildingMOTIF model *instance* and `Model`
2. loading `Libraries` into a BuildingMOTIF instance
3. adding to a model by *evaluating* `Templates`
```

[^1]: https://www.energycodes.gov/prototype-building-models#Commercial
[^2]: https://www.w3.org/TR/turtle/
[^3]: https://www.w3.org/RDF/

## Creating a Model

BuildingMOTIF needs a database to store models, libraries, templates, ontologies, and other data. This database can be *in-memory* (which will be deleted when the process ends) or *persistent*. For simplicity, we will start with an in-memory database where `bm` represents a BuildingMOTIF instance.

```{code-cell}
from buildingmotif import BuildingMOTIF
bm = BuildingMOTIF("sqlite://") # in-memory instance
```

```{margin}
```{note}
A `Model` is an RDF graph representing part or all of a building.
```

Now that we have a BuildingMOTIF instance, we can create a `Model`. Creating a model requires importing the `Model` class, creating an RDF namespace to hold all of the entities in the model, and telling BuildingMOTIF to create a new model with that namespace. The namespace is a URL used to uniquely identify the model.

```{code-cell}
from rdflib import Namespace
from buildingmotif.dataclasses import Model

# create the namespace
BLDG = Namespace('urn:bldg/')

# Create the model! This will raise an exception if the namespace is not syntactically valid.
model = Model.create(BLDG, description="This is a test model for a simple building") 
```

We can print out the contents of the model by accessing the `.graph` property of the model object. Printing this out reveals that BuildingMOTIF has added a couple annotations to the model for us, but there is otherwise no metadata about the building itself:

```{code-cell}
print(model.graph.serialize())
```

The `model.graph` object is just the RDFLib Graph[^4] that stores the model. You can interact with the graph by adding triples with `model.graph.add((subject, predicate, object))` but as we will soon see, BuildingMOTIF can automate some of that!

[^4]: https://rdflib.readthedocs.io/

## Loading Libraries

```{margin}
```{note}
`Libraries` are collections of Templates and Shapes.
```

Before we can add semantic metadata to the model, we need to import some `Libraries`. We import libraries by calling `Library.load` in BuildingMOTIF. Libraries can be loaded from directories containing `.yml` and `.ttl` files (for Templates and Shapes, respectively), or from ontology files directly. The code below contains an example of importing the `brick` library, which is simply the Brick ontology. This allows BuildingMOTIF to take advantage of the classes and relationships defined by Brick when validating the model. Loading in these definitions also allows other libraries to refer to Brick definitions. You can also ask a library for the names of the templates it defines, which we'll limit to the first ten below.

```{code-cell}
# load a library
from buildingmotif.dataclasses import Library
brick = Library.load(ontology_graph="../../libraries/brick/Brick-subset.ttl")

# print the first 10 templates
print("The Brick library contains the following templates:")
for template in brick.get_templates()[:10]:
    print(f"  - {template.name}")
```

## Adding to a Model with Templates

### Exploring a Template

```{margin}
```{note}
`Templates` are functions that generate parts of an RDF model.
```

`Templates` make it easy to add metadata to a model without having to touch any RDF at all by generating parts of an RDF graph. This graph may represent a simple device like a fan, a complex entity like a chilled water system, or other parts of a building. The *body* of a template contains the basic structure of the graph representing that entity. Typically, a template defines several *parameters* that represent user-provided input necessary to create that entity in the model.

Let's start with the template for an air handling unit (AHU) from the `brick` library, which we can fetch out of the library by referring to it by name. Then, let's ask the template for the parameters it defines. 

```{code-cell}
# import this to make writing URIs easier
from buildingmotif.namespaces import BRICK

# get template
ahu_template = brick.get_template_by_name(BRICK.AHU)

# print template parameters
print("The template has the following parameters:")
for param in ahu_template.parameters:
    print(f"  {param}")
```

All templates have a mandatory `name` parameter. We can also print out the body of the template to see how those parameters will be used. Any URI that starts with a `p:` is a parameter.

```{code-cell}
print(ahu_template.body.serialize())
```

### Evaluating a Template

```{margin}
```{note}
For now, provide all of the parameters to the Template when evaluating. BuildingMOTIF does support partial evaluation of Templates but this is not necessary to understand or use when starting out.
```

Now that we know what the template looks like and what parameters it needs, we can *evaluate* the Template. *Evaluation* is the process of turning a template into a graph that can be added to a model. We accomplish this with the `evaluate` function, which takes a dictionary of *bindings* as an argument. Bindings relate a parameter in the template to a value (typically a URI in your building's namespace). Put another way, the *keys* of the dictionary are the names of the parameters and the *values* of the dictionary are what will replace that parameter in the template's body.

Let's create an AHU named *Core_ZN-PSZ_AC*, which represents the core zone's packaged single zone air conditioner in the Small Office model, and take a look at the result of evaluating the template.

```{margin}
```{note}
When creating a real Brick model, you would use BMS point names, equipment schedules, etc. to determine the correct names of these entities. Other tutorials will cover how to use BuildingMOTIF with these kinds of metadata sources.
```

```{code-cell}
ahu_name = "Core_ZN-PSC_AC"
ahu_binding_dict = {"name": BLDG[ahu_name]}
ahu_graph = ahu_template.evaluate(ahu_binding_dict)

# ahu_graph is just an instance of rdflib.Graph
print(ahu_graph.serialize())
```

### Adding Evaluated Templates to the Model

```{margin}
```{note}
If using a persistent (disk-backed) instance of BuildingMOTIF instead of an in-memory instance, be sure to use `bm.session.commit()` to save your work after calling `add_graph`.
```

Now that we have an RDF graph representing an AHU, let's add it to the model using the `add_graph` function. 

```{code-cell}
model.add_graph(ahu_graph)
print(model.graph.serialize())
```

Next, we'll add some of the AHU's components (a fan, a damper, and a cooling coil) to the model using Templates. Then we'll connect the components to the AHU using RDFLib's `graph.add((subject, predicate, object))` method.

```{code-cell}
# templates
oa_ra_damper_template = brick.get_template_by_name(BRICK.Damper)
fan_template = brick.get_template_by_name(BRICK.Supply_Fan)
clg_coil_template = brick.get_template_by_name(BRICK.Cooling_Coil)

# add fan
fan_name = f"{ahu_name}-Fan"
fan_binding_dict = {"name": BLDG[fan_name]}
fan_graph = fan_template.evaluate(fan_binding_dict)
model.add_graph(fan_graph)

# add outdoor air/return air damper
oa_ra_damper_name = f"{ahu_name}-Damper"
oa_ra_damper_binding_dict = {"name": BLDG[oa_ra_damper_name]}
oa_ra_damper_graph = oa_ra_damper_template.evaluate(oa_ra_damper_binding_dict)
model.add_graph(oa_ra_damper_graph)

# add clg coil
clg_coil_name = f"{ahu_name}-Clg_Coil"
clg_coil_binding_dict = {"name": BLDG[clg_coil_name]}
clg_coil_graph = clg_coil_template.evaluate(clg_coil_binding_dict)
model.add_graph(clg_coil_graph)

# connect fan, damper, and clg coil to AHU
model.graph.add((BLDG[ahu_name], BRICK.hasPart, BLDG[oa_ra_damper_name]))
model.graph.add((BLDG[ahu_name], BRICK.hasPart, BLDG[fan_name]))
model.graph.add((BLDG[ahu_name], BRICK.hasPart, BLDG[clg_coil_name]))

# print model to confirm components were added and connected
print(model.graph.serialize())
```

```{attention}
If you want some additional practice, try writing some Python code that adds a Brick `Heating_Coil` to the model and connects it to the AHU.
```

```{hint}
:class: dropdown

```python
# get template
htg_coil_template = brick.get_template_by_name(BRICK.Heating_Coil)

# add htg coil
htg_coil_name = f"{ahu_name}-Htg_Coil"
htg_coil_binding = {"name": BLDG[htg_coil_name]}
htg_coil_graph = htg_coil_template.evaluate(htg_coil_binding)
model.add_graph(htg_coil_graph)

# connect htg coil to AHU
model.graph.add((BLDG[ahu_name], BRICK.hasPart, BLDG[htg_coil_name]))

# print model to confirm component was added and connected
print(model.graph.serialize())
```

Finally, let's save the model to use in the next tutorial.

```{code-cell}
#save model
model.graph.serialize(destination="tutorial1_model.ttl")
```
