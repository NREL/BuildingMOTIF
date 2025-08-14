from rdflib import Graph, URIRef
from rdflib.namespace import RDF
from buildingmotif.namespaces import OWL
from buildingmotif.dataclasses import Library, Model


def test_get_model_manifest_json_includes_body_and_uris(client, building_motif):
    # Setup: empty manifest
    model = Model.create(name="urn:my_model")

    # Act: request JSON
    res = client.get(f"/models/{model.id}/manifest", headers={"Accept": "application/json"})

    # Assert
    assert res.status_code == 200
    payload = res.get_json()
    assert set(payload.keys()) == {"body", "library_uris"}
    # body should be parseable TTL
    Graph().parse(data=payload["body"], format="turtle")
    assert payload["library_uris"] == []


def test_post_model_manifest_with_library_ids_sets_imports(client, building_motif):
    # Setup
    model = Model.create(name="urn:my_model_ids")
    lib = Library.create("lib_ids")
    db_lib = building_motif.table_connection.get_db_library(lib.id)
    db_lib.shape_collection.graph_id = "urn:test:lib_ids_sc"
    building_motif.session.commit()

    # Act
    res = client.post(
        f"/models/{model.id}/manifest",
        json={"library_ids": [lib.id]},
        headers={"Content-Type": "application/json"},
    )

    # Assert
    assert res.status_code == 200
    g = Graph().parse(data=res.data, format="turtle")
    subject = URIRef(str(model.name))
    assert (subject, OWL.imports, URIRef("urn:test:lib_ids_sc")) in g


def test_post_model_manifest_with_library_uris_sets_imports(client, building_motif):
    # Setup
    model = Model.create(name="urn:my_model_uris")
    uris = ["urn:test:sc1", "urn:test:sc2"]

    # Act
    res = client.post(
        f"/models/{model.id}/manifest",
        json={"library_uris": uris},
        headers={"Content-Type": "application/json"},
    )

    # Assert
    assert res.status_code == 200
    g = Graph().parse(data=res.data, format="turtle")
    subject = URIRef(str(model.name))
    for u in uris:
        assert (subject, OWL.imports, URIRef(u)) in g


def test_post_model_manifest_replace_with_turtle_body(client, building_motif):
    # Setup
    model = Model.create(name="urn:my_model_replace")
    manifest_ttl = """
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        <urn:new-manifest> a owl:Ontology .
    """

    # Act
    res = client.post(
        f"/models/{model.id}/manifest",
        data=manifest_ttl,
        headers={"Content-Type": "text/turtle"},
    )

    # Assert
    assert res.status_code == 200
    returned = Graph().parse(data=res.data, format="turtle")
    posted = Graph().parse(data=manifest_ttl, format="turtle")
    assert set(returned) == set(posted)


def test_get_model_manifest_turtle_when_requested(client, building_motif):
    # Setup
    model = Model.create(name="urn:my_model_ttl")

    # Act
    res = client.get(
        f"/models/{model.id}/manifest",
        headers={"Accept": "text/turtle"},
    )

    # Assert
    assert res.status_code == 200
    Graph().parse(data=res.data, format="turtle")  # parses without error


def test_post_model_manifest_bad_json_types_returns_400(client, building_motif):
    # Setup
    model = Model.create(name="urn:my_model_badjson")

    # Act
    res = client.post(
        f"/models/{model.id}/manifest",
        json={"library_ids": "not-a-list", "library_uris": ["ok"]},
        headers={"Content-Type": "application/json"},
    )

    # Assert
    assert res.status_code == 400
