from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.db_connections.graph_connection import GraphConnection
from tests.conftest import MockBuildingMotif

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SMALL_OFFICE_BRICK_TTL = FIXTURES_DIR / "smallOffice_brick.ttl"
DB_FILE = FIXTURES_DIR / "smallOffice.db"


@pytest.fixture
def graph_connection(tmpdir):
    temp_db_path = tmpdir / "temp.db"
    uri = Literal(f"sqlite:///{temp_db_path}")
    bm = MockBuildingMotif(uri)

    graph_connection = GraphConnection(bm.engine, bm)
    yield graph_connection

    bm.session.commit()
    bm.release()


def test_create_graph(graph_connection):
    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)

    res = graph_connection.create_graph("my_graph", g)

    isomorphic(res, g)
    assert graph_connection.get_all_graph_identifiers() == ["my_graph"]


@pytest.mark.skip(reason="empty graphs can't be entered")
def test_create_empty_graph(graph_connection):
    g = Graph()

    graph_connection.create_graph("my_graph", g)

    assert graph_connection.get_all_graph_identifiers() == ["my_graph"]


def test_get_graph(graph_connection):
    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)
    graph_connection.create_graph("my_graph", g)

    res = graph_connection.get_graph("my_graph")

    assert isomorphic(res, g)


@pytest.mark.skip(reason="a non-existant graph will just come back empty")
def test_get_graph_does_not_exist(graph_connection):
    with pytest.raises(ValueError):
        graph_connection.get_graph("I don't exist")


def test_delete_graph(graph_connection):
    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)
    graph_connection.create_graph("my_graph", g)

    assert graph_connection.get_all_graph_identifiers() == ["my_graph"]
    graph_connection.delete_graph("my_graph")
    assert graph_connection.get_all_graph_identifiers() == []
