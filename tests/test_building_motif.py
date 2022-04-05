import os
import tempfile

import pytest
import rdflib
from rdflib import RDF, Graph, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.building_motif import BuildingMotif
from buildingmotif.data_classes import Model


@pytest.fixture
def clean_building_motif():
    BuildingMotif.clean()
    with tempfile.TemporaryDirectory() as tempdir:
        temp_db_path = os.path.join(tempdir, "temp.db")
        uri = f"sqlite:///{temp_db_path}"
        building_motif = BuildingMotif(uri)
        yield building_motif
        BuildingMotif.clean()


def test_create_model(clean_building_motif):
    bm = clean_building_motif

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)

    model = bm.create_model(name="my_model", graph=g)

    assert isinstance(model, Model)
    assert model.name == "my_model"
    assert isinstance(model.graph, rdflib.Graph)
    assert isomorphic(model.graph, g)


def test_get_model(clean_building_motif):
    bm = clean_building_motif

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)

    model = bm.create_model(name="my_model", graph=g)
    model = bm.get_model(id=model.id)

    assert isinstance(model, Model)
    assert model.name == "my_model"
    assert isinstance(model.graph, rdflib.Graph)
    assert isomorphic(model.graph, g)


def test_save_model(clean_building_motif):
    bm = clean_building_motif

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)
    model = bm.create_model(name="my_model", graph=g)

    model.name = "boo!"
    new_triples = [
        (URIRef("http://example.org/alex"), RDF.type, FOAF.Person),
        (URIRef("http://example.org/hannah"), RDF.type, FOAF.Project),
    ]
    model.graph.remove(hannahs_personhood)
    model.graph += new_triples

    bm.save_model(model)
    model = bm.get_model(model.id)

    assert model.name == "boo!"
    assert isomorphic(model.graph, new_triples)


def test_delete_model(clean_building_motif):
    bm = clean_building_motif

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)

    model = bm.create_model(name="my_model", graph=g)

    assert len(bm.table_con.get_all_db_models()) == 1
    assert len(bm.graph_con.get_all_graph_identifiers()) == 1

    bm.delete_model(model)

    assert len(bm.table_con.get_all_db_models()) == 0
    assert len(bm.graph_con.get_all_graph_identifiers()) == 0
