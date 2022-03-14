from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.db_connections.graph_connection import GraphConnection

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SMALL_OFFICE_BRICK_TTL = FIXTURES_DIR / "smallOffice_brick.ttl"
DB_FILE = FIXTURES_DIR / "smallOffice.db"


def make_test_graph_connect(dir):
    temp_db_path = dir / "temp.db"
    uri = Literal(f"sqlite:///{temp_db_path}")

    return GraphConnection(uri)


def test_create_graph(tmpdir):
    gc = make_test_graph_connect(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)

    res = gc.create_graph("my_graph", g)

    isomorphic(res, g)
    assert gc.get_all_graph_identifiers() == ["my_graph"]


@pytest.mark.skip(reason="empty graphs can't be entered")
def test_create_empty_graph(tmpdir):
    gc = make_test_graph_connect(tmpdir)

    g = Graph()

    gc.create_graph("my_graph", g)

    assert gc.get_all_graph_identifiers() == ["my_graph"]


def test_get_graph(tmpdir):
    gc = make_test_graph_connect(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)
    gc.create_graph("my_graph", g)

    res = gc.get_graph("my_graph")

    assert isomorphic(res, g)


def test_update_graph(tmpdir):
    gc = make_test_graph_connect(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)
    gc.create_graph("my_graph", g)

    g = Graph()
    alexs_personhood = (URIRef("http://example.org/alex"), RDF.type, FOAF.Person)
    g.add(alexs_personhood)
    res = gc.update_graph("my_graph", g)

    assert isomorphic(res, g)


@pytest.mark.skip(reason="a non-existant graph will just come back empty")
def test_get_graph_does_not_exist(tmpdir):
    gc = make_test_graph_connect(tmpdir)

    with pytest.raises(ValueError):
        gc.get_graph("I don't exist")


def test_delete_graph(tmpdir):
    gc = make_test_graph_connect(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)
    gc.create_graph("my_graph", g)

    assert gc.get_all_graph_identifiers() == ["my_graph"]
    gc.delete_graph("my_graph")
    assert gc.get_all_graph_identifiers() == []
