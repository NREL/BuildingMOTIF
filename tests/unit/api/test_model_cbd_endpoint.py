from rdflib import Graph, URIRef
from buildingmotif.dataclasses import Model


def test_get_model_cbd_endpoint_basic_and_self_contained(client, building_motif):
    # Setup
    model = Model.create(name="urn:my_model_cbd_api")
    s = URIRef("urn:ex:s")
    p = URIRef("urn:ex:p")
    o1 = URIRef("urn:ex:o1")
    o2 = URIRef("urn:ex:o2")

    # s -> o1; and o1 -> o2
    model.add_triples((s, p, o1))
    model.add_triples((o1, p, o2))

    # Persist if needed
    building_motif.session.commit()

    # Act: self_contained=false should only include triples where subject == s
    res = client.get(f"/models/{model.id}/cbd", query_string={"node": str(s), "self_contained": "false"})
    assert res.status_code == 200, res.data
    g = Graph().parse(data=res.data, format="turtle")
    assert (s, p, o1) in g
    assert (o1, p, o2) not in g

    # Act: self_contained=true should include follow-on triples starting at o1
    res2 = client.get(f"/models/{model.id}/cbd", query_string={"node": str(s), "self_contained": "true"})
    assert res2.status_code == 200, res2.data
    g2 = Graph().parse(data=res2.data, format="turtle")
    assert (s, p, o1) in g2
    assert (o1, p, o2) in g2


def test_get_model_cbd_endpoint_missing_node_returns_400(client, building_motif):
    model = Model.create(name="urn:my_model_cbd_api2")
    res = client.get(f"/models/{model.id}/cbd")
    assert res.status_code == 400
