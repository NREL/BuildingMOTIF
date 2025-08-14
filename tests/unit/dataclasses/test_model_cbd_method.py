from rdflib import URIRef
from buildingmotif.dataclasses import Model


def test_model_cbd_method(building_motif):
    # Setup
    model = Model.create(name="urn:my_model_cbd_method")
    s = URIRef("urn:ex:s")
    p = URIRef("urn:ex:p")
    o1 = URIRef("urn:ex:o1")
    o2 = URIRef("urn:ex:o2")

    # s -> o1; and o1 -> o2
    model.add_triples((s, p, o1))
    model.add_triples((o1, p, o2))

    # Act: non self-contained
    cbd = model.node_subgraph(s, self_contained=False)
    assert (s, p, o1) in cbd
    assert (o1, p, o2) not in cbd

    # Act: self-contained expands
    cbd2 = model.node_subgraph(s, self_contained=True)
    assert (s, p, o1) in cbd2
    assert (o1, p, o2) in cbd2
