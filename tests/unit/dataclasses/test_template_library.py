import pytest
from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF

from buildingmotif.dataclasses import TemplateLibrary


def test_create(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")

    assert tl.name == "my_template_library"
    assert isinstance(tl.id, int)

    also_tl = TemplateLibrary.load(tl.id)

    assert also_tl.name == "my_template_library"
    assert also_tl.id == tl.id


def test_update_name(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")

    assert tl.name == "my_template_library"

    tl.name = "a_new_name"
    assert tl.name == "a_new_name"


def test_update_id(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")

    with pytest.raises(AttributeError):
        tl.id = 1


def test_get_templates(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t1 = tl.create_template("my_template")
    t2 = tl.create_template("your_template")

    results = tl.get_templates()
    assert len(results) == 2
    assert [r.id for r in results] == [t1.id, t2.id]


def test_get_shape_collection(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    shape_collection = tl.get_shape_collection()
    shape_collection.graph.add(
        (URIRef("http://example.org/alex"), RDF.type, FOAF.Person)
    )

    assert tl.get_shape_collection() == shape_collection
    assert isomorphic(
        shape_collection.load(shape_collection.id).graph, shape_collection.graph
    )
