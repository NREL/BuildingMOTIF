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
This tutorial assumes that `BuildingMOTIF` has already been installed in the local environment with the `bacnet-ingress` option (`pip install buildingmotif[bacnet-ingress]`) **and** that the user has access to a BACnet network with descriptive names. One easy way of *emulating* a BACnet network is to use the [Simulated Digital Twin](https://github.com/gtfierro/simulated-digital-twin) repository.
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
brick = Library.load(ontology_graph="../../libraries/brick/Brick-subset.ttl")
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
brick = BACnetToBrickIngress(bm, bacnet)
# creates the graph from the BACnet records
bacnet_network_graph = brick.graph(BLDG)
# add the graph to our model
model.add_graph(bacnet_network_graph)
```

We can now take a look at the resulting graph:

```{code-cell}
print(model.graph.serialize())
```

We can now see the devices and their objects represented in the model. However, the metadata is not very descriptive. All of the BACnet objects have been inferred to be instances of `brick:Point`.
In the next step, we will use BuildingMOTIF to incorporate our other knowledge about the building to augment this Brick model with more descriptive metadata.
