from urllib.parse import quote

from rdflib import Graph, URIRef

from buildingmotif.dataclasses import Library


def test_get_graph_by_id_returns_graph(client, building_motif):
    # Setup a shape collection with some triples
    lib = Library.create("lib_graph_fetch")
    sc = lib.get_shape_collection()
    sc.graph.parse(
        data="""
@prefix : <urn:g#> .
:s :p :o .
""",
        format="turtle",
    )
    building_motif.session.commit()

    # Resolve its underlying named graph identifier
    db_lib = building_motif.table_connection.get_db_library(lib.id)
    graph_id = db_lib.shape_collection.graph_id

    # Act
    results = client.get(f"/graph/{quote(graph_id, safe='')}")

    # Assert
    assert results.status_code == 200
    g = Graph().parse(data=results.data, format="turtle")
    assert (URIRef("urn:g#s"), URIRef("urn:g#p"), URIRef("urn:g#o")) in g


def test_get_graph_by_id_not_found(client):
    missing = "urn:does:not:exist"
    results = client.get(f"/graph/{quote(missing, safe='')}")
    assert results.status_code == 404
    assert results.json == {"message": f"ID: {missing}"}
