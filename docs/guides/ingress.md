# Ingresses

*Ingresses* are BuildingMOTIF's mechanism for importing metadata from external sources.
The `Ingress` APIs are deliberately general so that they can be easily extended to new metadata sources.

Briefly, there is an abstract `IngressHandler` class (`buildingmotif.ingresses.base.IngressHandler`) with two abstract subclasses: `RecordIngressHandler` and `GraphIngressHandler`.
Users of the `Ingress` API should subclasses these two classes to specialize (and indeed provide) their behavior.

## Ingress Types

### Graph Ingress Handler

`GraphIngressHandler` defines one method: `graph(ns: rdflib.Namespace) -> rdflib.Graph`.
The `rdflib.Graph` returned by this method contains RDF data (inferred, translated, computed, etc) from some underlying source.
`GraphIngressHandler`s source their metadata from either an upstream `RecordIngressHandler` or any other source provided in the instantiation of the `GraphIngressHandler` subclass.

Any new entities/URIs/etc created or inferred by the `GraphIngressHandler` should be placed into the provided namespace (`ns`).
An instance of `GraphIngressHandler` is typically at the *end* of a pipeline of `IngressHandler`s.

### Record Ingress Handler

`RecordIngressHandler` defines one method: `records() -> List[Record]`.
A `Record` is a simple Python data structure:

```python
@dataclass
class Record:
    # an arbitrary "type hint"
    rtype: str
    # possibly-nested dictionary of (semi-)structured data from
    # the underlying source
    fields: dict
```

The choice of values for the `Record` is up to each `RecordIngressHandler` instance.

## Example: BACnet to Brick
