import pytest
from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.dataclasses import Library


def test_create(clean_building_motif):
    lib = Library.create("my_library")

    assert lib.name == "my_library"
    assert isinstance(lib.id, int)

    also_lib = Library.load(lib.id)

    assert also_lib.name == "my_library"
    assert also_lib.id == lib.id


def test_update_name(clean_building_motif):
    lib = Library.create("my_library")

    assert lib.name == "my_library"

    lib.name = "a_new_name"
    assert lib.name == "a_new_name"


def test_update_id(clean_building_motif):
    lib = Library.create("my_library")

    with pytest.raises(AttributeError):
        lib.id = 1


def test_get_templates(clean_building_motif):
    lib = Library.create("my_library")
    t1 = lib.create_template("my_template")
    t2 = lib.create_template("your_template")

    results = lib.get_templates()
    assert len(results) == 2
    assert [r.id for r in results] == [t1.id, t2.id]


def test_get_shape_collection(clean_building_motif):
    lib = Library.create("my_library")
    shape_collection = lib.get_shape_collection()
    shape_collection.graph.add(
        (URIRef("http://example.org/alex"), RDF.type, FOAF.Person)
    )

    assert lib.get_shape_collection() == shape_collection
    assert isomorphic(
        shape_collection.load(shape_collection.id).graph, shape_collection.graph
    )
