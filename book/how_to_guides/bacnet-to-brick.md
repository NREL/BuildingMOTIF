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

# Creating a Brick Model from a BACnet Network


```{margin}
```{important}
This tutorial assumes that `BuildingMOTIF` has already been installed in the local environment with the `bacnet-ingress` option **and** that the user has access to a BACnet network with descriptive names. One easy way of *emulating* a BACnet network is to use the [Simulated Digital Twin](https://github.com/gtfierro/simulated-digital-twin) repository.
```

The purpose of this how-to document is to demonstrate the creation of a functional Brick model from a BACnet network. This will be accomplished by using BuildingMOTIF's "ingresses" to import a BACnet network as a basic Brick model, and then using BuildingMOTIF to augment the basic Brick model with more descriptive metadata.

## External Setup

Make sure you have network access to a BACnet network, and that you are aware on what IP address that BACnet network can be reached. The simplest way to get this working is to use the [virtual machine setup in the simulated digital twin repository](https://github.com/gtfierro/simulated-digital-twin/tree/main/virtual-machine).

## BuildingMOTIF Setup

Like the previous tutorial, we'll create an in-memory BuildingMOTIF instance and load some libraries.

```{code-cell}
import logging
from rdflib import Namespace
from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Model, Library
from buildingmotif.namespaces import BRICK # import this to make writing URIs easier

# in-memory instance
bm = BuildingMOTIF("sqlite://", log_level=logging.ERROR)

# create the namespace for the building
BLDG = Namespace('urn:bldg/')

# create the building model
model = Model.create(BLDG, description="This is a test model for a simple building")

# load some libraries we will use later
brick = Library.load(ontology_graph="../../libraries/brick/Brick.ttl")
constraints = Library.load(ontology_graph="../../buildingmotif/resources/constraints.ttl")
```

## Pulling in BACnet Metadata

We use the `buildingmotif.ingresses.bacnet.BACnetNetwork` ingress module to pull structured information from the BACnet network. The ingress module scrapes the BACnet network and produces a set of "records" which correspond to the individual BACnet Devices and Objects discovered in the network.

```{code-cell}
from buildingmotif.ingresses.bacnet import BACnetNetwork

bacnet = BACnetNetwork("10.47.35.1/24")
for rec in bacnet.records[:10]:  # just print the first 10
    print(rec)
```

Each of these records has an `rtype` field, which is used by the ingress implementation to differentiate between different kinds of records; here it differentiates between BACnet Devices and BACnet Objects, which have different expressions in Brick. The `fields` attribute cotnains arbitrary key-value pairs, again defined by the ingress implementation, which can be interpreted by another ingress module.

## BACnet to Brick: an Initial Model

We use the `buildingmotif.ingresses.brick.BACnetToBrickIngress` ingress module to turn the `Record`s from the `BACnetNetwork` ingress into a Brick model. This is as simple as choosing a namespace for the entities (this is usually just the same namespace used for the Model, i.e. `BLDG` above) and connecting our new ingress module instance to the existing BACnet network ingress module.


```{code-cell}
from buildingmotif.ingresses.brick import BACnetToBrickIngress

# create the Brick ingress module and connect to the existing bacnet module
brick2bacnet = BACnetToBrickIngress(bm, bacnet)
# creates the graph from the BACnet records
bacnet_network_graph = brick2bacnet.graph(BLDG)
# add the graph to our model
model.add_graph(bacnet_network_graph)
```

We can now take a look at the resulting graph:

```{code-cell}
print(model.graph.serialize())
```

We can now see the devices and their objects represented in the model. However, the metadata is not very descriptive. All of the BACnet objects have been inferred to be instances of `brick:Point`.
In the next step, we will use BuildingMOTIF to incorporate our other knowledge about the building to augment this Brick model with more descriptive metadata.

## Augmenting the Initial Model: Our Strategy

There is [existing documentation](https://docs.brickschema.org/lifecycle/creation.html) on techniques for inferring Brick metadata from point labels. Below, we will show how a simple Python-based point type inference module can be implemented by extending BuildingMOTIF's existing ingress module implementation. Then, we will use BuildingMOTIF's templates to incorporate the inferred points into a bigger model.

## Point Type Inference

For completeness, here are the names of the 5 points in the BACnet network scanned above (these will be different if you are not using the Simulated Digital Twin platform):

- `hvac_oveAhu_yPumHea_u`
- `hvac_oveZonSupSou_TZonCooSet_u`
- `hvac_oveZonSupSou_TZonHeaSet_u`
- `hvac_reaZonSou_TSup_y`
- `hvac_reaZonSou_TZon_y`

Squinting at these point names, we might see how we can divide each name into sections: `hvac_<equip or zone name>_<point type>_<u or y>`. Let's write Python code to pull out the Brick metadata we can from these labels.

```{code-cell}
from rdflib import Graph, URIRef
from buildingmotif.namespaces import RDF, BRICK
def parse_label(label: str, output: Graph):
    """Parses the label and puts the resulting triples in the provided graph."""
    parts = label.split('_')
    _, _, point_type, _ = parts # throw away everything that's not the point type

    if point_type == 'TZonCooSet':
        brick_class = BRICK.Zone_Air_Cooling_Temperature_Setpoint
    elif point_type == 'TZonHeaSet':
        brick_class = BRICK.Zone_Air_Heating_Temperature_Setpoint
    elif point_type == 'TSup':
        brick_class = BRICK.Supply_Air_Temperature_Sensor
    elif point_type == 'TZon':
        brick_class = BRICK.Zone_Air_Temperature_Sensor
    elif point_type == 'yPumHea':
        brick_class = BRICK.Heating_Command
    else:
        raise Exception("Unknown point type!")

    output.add((BLDG[label], RDF.type, brick_class))
```

We can wrap this function in an ingress module so it is easy to reuse later. This just requires a little bit of moving some code around

```{code-cell}
from buildingmotif.ingresses.base import GraphIngressHandler

class MyPointParser(GraphIngressHandler):
    def __init__(self, bm: BuildingMOTIF, upstream: GraphIngressHandler):
        self.bm = bm
        self.upstream = upstream # this will point to our BACnetToBrickIngress handler

    def parse_label(self, label: str, entity: URIRef, output: Graph):
        """Parses the label and puts the resulting triples in the provided graph.
        Adds the type to the indicated entity"""
        parts = label.split('_')
        _, _, point_type, _ = parts # throw away everything that's not the point type

        if point_type == 'TZonCooSet':
            brick_class = BRICK.Zone_Air_Cooling_Temperature_Setpoint
        elif point_type == 'TZonHeaSet':
            brick_class = BRICK.Zone_Air_Heating_Temperature_Setpoint
        elif point_type == 'TSup':
            brick_class = BRICK.Supply_Air_Temperature_Sensor
        elif point_type == 'TZon':
            brick_class = BRICK.Zone_Air_Temperature_Sensor
        elif point_type == 'yPumHea':
            brick_class = BRICK.Heating_Command
        else:
            raise Exception("Unknown point type!")

        output.add((entity, RDF.type, brick_class))

    def graph(self, ns: Namespace) -> Graph:
        """the method we override to implement a GraphIngressHandler"""
        output_graph = Graph()
        bacnet_graph = self.upstream.graph(ns)
        point_labels = bacnet_graph.query("""
            SELECT ?entity ?label WHERE {
                ?entity <https://brickschema.org/schema/ref#hasExternalReference> ?ref .
                ?ref <http://data.ashrae.org/bacnet/2020#object-name> ?label
            }""")
        for entity, label in point_labels:
            # infer type for each
            self.parse_label(label, entity, output_graph)

        return output_graph
```

Now we can invoke our ingress module:

```{code-cell}
# create the Brick ingress module and connect to the existing bacnet module
point_ingress = MyPointParser(bm, brick2bacnet)
# creates the graph from the BACnet records
augmented_graph = point_ingress.graph(BLDG)
# add the graph to our model
model.add_graph(augmented_graph)
```

and display the resulting model

```{code-cell}
print(model.graph.serialize())
```

We can now see that the points in our model have more descriptive Brick types.

## Creating a More Complete Model with Templates

We can now focus on associating these points with real equipment and zones to create a more complete Brick model. The most straightforward way of doing this is to create templates that convey what we think the parts of the building should look like.

```{margin}
```{info}
As BuildingMOTIF gets more mature, there will be a larger ecosystem of Templates and Shapes we can draw from. For this (simple) example, we will create our own Templates that match the limited metadata we have about the sample building.
```

Let's create two templates: one for an HVAC zone and one for a VAV box.

```yml
sample-hvac-zone:
  body: >
    @prefix p: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    p:name a brick:HVAC_Zone ;
        brick:hasPoint p:zone-temp .
  dependencies:
  - template: https://brickschema.org/schema/Brick#Zone_Air_Temperature_Sensor
    library: https://brickschema.org/schema/1.3/Brick
    args: {"name": "zone-temp"}
sample-vav:
  body: >
    @prefix p: <urn:___param___#> .
    @prefix brick: <https://brickschema.org/schema/Brick#> .
    p:name a brick:VAV ;
        brick:hasPoint p:sup-temp, p:heat-sp, p:cool-sp ;
        brick:feeds p:zone .
  dependencies:
  - template: https://brickschema.org/schema/Brick#Supply_Air_Temperature_Sensor
    library: https://brickschema.org/schema/1.3/Brick
    args: {"name": "sup-temp"}
  - template: https://brickschema.org/schema/Brick#Zone_Air_Heating_Temperature_Setpoint
    library: https://brickschema.org/schema/1.3/Brick
    args: {"name": "heat-sp"}
  - template: https://brickschema.org/schema/Brick#Zone_Air_Cooling_Temperature_Setpoint
    library: https://brickschema.org/schema/1.3/Brick
    args: {"name": "cool-sp"}
  - template: sample-hvac-zone
    args: {"nzme": "zone"}
```

We load this library into BuildingMOTIF:

```{code-cell}
templates = Library.load(directory="libraries/bacnet-to-brick-templates")
```
