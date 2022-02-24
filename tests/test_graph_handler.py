from pathlib import Path

import pytest
from rdflib import RDF, Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.graph_handler import GraphHandler

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SMALL_OFFICE_BRICK_TTL = FIXTURES_DIR / "smallOffice_brick.ttl"
DB_FILE = FIXTURES_DIR / "smallOffice.db"


def make_test_graph_handler(dir):
    temp_db_path = dir / "temp.db"
    uri = Literal(f"sqlite:///{temp_db_path}")

    return GraphHandler(uri)


def test_create_graph(tmpdir):
    gh = make_test_graph_handler(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)

    res = gh.create_graph("my_graph", g)

    isomorphic(res, g)
    assert gh.get_all_graph_identifiers() == ["my_graph"]


@pytest.mark.skip(reason="empty graphs can't be entered")
def test_create_empty_graph(tmpdir):
    gh = make_test_graph_handler(tmpdir)

    g = Graph()

    gh.create_graph("my_graph", g)

    assert gh.get_all_graph_identifiers() == ["my_graph"]


def test_get_graph(tmpdir):
    gh = make_test_graph_handler(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)
    gh.create_graph("my_graph", g)

    res = gh.get_graph("my_graph")

    assert isomorphic(res, g)


@pytest.mark.skip(reason="a non-existant graph will just come back empty")
def test_get_graph_does_not_exist(tmpdir):
    gh = make_test_graph_handler(tmpdir)

    with pytest.raises(ValueError):
        gh.get_graph("I don't exist")


def test_delete_graph(tmpdir):
    gh = make_test_graph_handler(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)
    gh.create_graph("my_graph", g)

    assert gh.get_all_graph_identifiers() == ["my_graph"]
    gh.delete_graph("my_graph")
    assert gh.get_all_graph_identifiers() == []
