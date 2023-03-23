# Ingresses

*Ingresses* are BuildingMOTIF's mechanism for importing metadata from external sources.
The `Ingress` APIs are deliberately general so that they can be easily extended to new metadata sources.

`IngressHandler` has two abstract subclasses:
- [`RecordIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.base.html#buildingmotif.ingresses.base.RecordIngressHandler), which produces `Record`s
- [`GraphIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.base.html#buildingmotif.ingresses.base.GraphIngressHandler), which produces `Graph`s

Every concrete `IngressHandler` should inherit from one of these two classes.

## Ingress Types

### Record Ingress Handler

[`RecordIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.base.html#buildingmotif.ingresses.base.RecordIngressHandler) defines one method: `records() -> List[Record]`.

A `Record` is a simple Python data structure:

```python
@dataclass
class Record:
    # a "type hint" or other identifier for an application-defined category of Records
    rtype: str
    # key-value pairs of data from the underlying source. Application-defined structure
    fields: dict
```

The choice of values for the `Record` is up to each `RecordIngressHandler` instance.

### Graph Ingress Handler

[`GraphIngressHandler`](/reference/apidoc/_autosummary/buildingmotif.ingresses.base.html#buildingmotif.ingresses.base.GraphIngressHandler) defines one method: `graph(ns: rdflib.Namespace) -> rdflib.Graph`.

The `rdflib.Graph` returned by this method contains RDF data (inferred, translated, computed, etc) from some underlying source.
`GraphIngressHandler`s source their metadata from either an upstream `RecordIngressHandler` or any other source provided in the instantiation of the `GraphIngressHandler` subclass.

Any new entities/URIs/etc created or inferred by the `GraphIngressHandler` should be placed into the provided namespace (`ns`).
An instance of `GraphIngressHandler` is typically at the *end* of a pipeline of `IngressHandler`s.

## Usage Example: BACnet to Brick

To illustrate use of the `Ingress` API we show how to use two ingress handlers provided by BuildingMOTIF to construct a Brick model from a BACnet network.

We will use `buildingmotif.ingresses.bacnet.BACnetNetwork` (a `RecordIngressHandler`) to pull some `Record`s out of a BACnet network.
These `Record`s will represent BACnet objects and devices; we use the `rtype` of each `Record`  to differentiate this.

```python
from buildingmotif.ingresses.bacnet import BACnetNetwork

# scan the 10.0.0.1/24 subnet for BACnet devices
network = BACnetNetwork(ip="10.0.0.1/24")
```
