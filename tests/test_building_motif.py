import rdflib
from rdflib import RDF, Graph, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.building_motif import BuildingMotif
from buildingmotif.data_classes import Model


def make_test_building_motif(dir):
    temp_db_path = dir / "temp.db"
    uri = f"sqlite:///{temp_db_path}"

    return BuildingMotif(uri)


def test_create_model(tmpdir):
    bmo = make_test_building_motif(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)

    model = bmo.create_model(name="my_model", graph=g)

    assert isinstance(model, Model)
    assert model.name == "my_model"
    assert isinstance(model.graph, rdflib.Graph)
    assert isomorphic(model.graph, g)


def test_get_model(tmpdir):
    bmo = make_test_building_motif(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)

    model = bmo.create_model(name="my_model", graph=g)
    model = bmo.get_model(id=model.id)

    assert isinstance(model, Model)
    assert model.name == "my_model"
    assert isinstance(model.graph, rdflib.Graph)
    assert isomorphic(model.graph, g)


def test_save_model(tmpdir):
    bmo = make_test_building_motif(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)
    model = bmo.create_model(name="my_model", graph=g)

    model.name = "boo!"
    new_triples = [
        (URIRef("http://example.org/alex"), RDF.type, FOAF.Person),
        (URIRef("http://example.org/hannah"), RDF.type, FOAF.Project),
    ]
    model.graph.remove(hannahs_personhood)
    model.graph += new_triples

    bmo.save_model(model)
    model = bmo.get_model(model.id)

    assert model.name == "boo!"
    assert isomorphic(model.graph, new_triples)


def test_delete_model(tmpdir):
    bmo = make_test_building_motif(tmpdir)

    g = Graph()
    hannahs_personhood = (URIRef("http://example.org/hannah"), RDF.type, FOAF.Person)
    g.add(hannahs_personhood)

    model = bmo.create_model(name="my_model", graph=g)

    assert len(bmo.table_con.get_all_db_models()) == 1
    assert len(bmo.graph_con.get_all_graph_identifiers()) == 1

    bmo.delete_model(model)

    assert len(bmo.table_con.get_all_db_models()) == 0
    assert len(bmo.graph_con.get_all_graph_identifiers()) == 0
