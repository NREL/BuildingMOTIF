import pytest
import rdflib
from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF
from sqlalchemy.exc import IntegrityError, NoResultFound

from buildingmotif.dataclasses import Template, TemplateLibrary
from buildingmotif.dataclasses.template import Dependency
from buildingmotif.template_compilation import compile_template_spec
from buildingmotif.utils import graph_size


def test_create(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template")

    assert isinstance(t, Template)
    assert isinstance(t.id, int)
    assert t.name == "my_template"
    assert isinstance(t.body, rdflib.Graph)

    also_t = tl.get_templates()[0]
    assert also_t.id == t.id
    assert also_t.name == t.name
    assert isomorphic(also_t.body, t.body)


def test_load(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template")
    t.body.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))

    result = Template.load(t.id)
    assert result.id == t.id
    assert result.name == t.name
    assert isomorphic(result.body, t.body)


def test_set_name(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template")

    t.name = "new name"
    assert t.name == "new name"


def test_update_id(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template")

    with pytest.raises(AttributeError):
        t.id = 1


def test_save_body(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template")

    assert isinstance(t, Template)
    assert isinstance(t.id, int)
    assert t.name == "my_template"
    assert isinstance(t.body, rdflib.Graph)

    triple = (URIRef("http://example.org/alex"), RDF.type, FOAF.Person)
    t.body.add(triple)

    also_t = Template.load(t.id)
    assert also_t.id == t.id
    assert also_t.name == t.name
    assert isomorphic(also_t.body, t.body)


def test_add_dependency(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant")
    dependee = tl.create_template("dependee")

    dependant.add_dependency(dependee, {"name": "1", "param": "2"})

    assert dependant.get_dependencies() == (
        Dependency(dependee.id, {"name": "1", "param": "2"}),
    )


def test_add_dependency_bad_args(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant")
    dependee = tl.create_template("dependee")

    with pytest.raises(ValueError):
        dependant.add_dependency(dependee, {"bad": "xyz"})


def test_add_dependency_already_exist(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant")
    dependee = tl.create_template("dependee")

    dependant.add_dependency(dependee, {"name": "1", "param": "2"})

    with pytest.raises(IntegrityError):
        dependant.add_dependency(dependee, {"name": "1", "param": "2"})

    clean_building_motif.session.rollback()


def test_get_dependencies(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant")
    dependee = tl.create_template("dependee")

    dependant.add_dependency(dependee, {"name": "1", "param": "2"})

    assert dependant.get_dependencies() == (
        Dependency(dependee.id, {"name": "1", "param": "2"}),
    )


def test_remove_dependency(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant")
    dependee = tl.create_template("dependee")

    dependant.add_dependency(dependee, {"name": "1", "param": "2"})
    assert dependant.get_dependencies() == (
        Dependency(dependee.id, {"name": "1", "param": "2"}),
    )

    dependant.remove_dependency(dependee)
    assert dependant.get_dependencies() == ()


def test_remove_depedancy_does_not_exist(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant")
    dependee = tl.create_template("dependee")

    with pytest.raises(NoResultFound):
        dependant.remove_dependency(dependee)

    clean_building_motif.session.rollback()


def test_template_compilation(clean_building_motif):
    spec = {
        "hasPoint": {
            "occ": "https://brickschema.org/schema/Brick#Occupancy_Sensor",
            "temp": "https://brickschema.org/schema/Brick#Temperature_Sensor",
            "sp": "https://brickschema.org/schema/Brick#Temperature_Setpoint",
        },
        "downstream": {"zone": "https://brickschema.org/schema/Brick#HVAC_Zone"},
    }
    spec = compile_template_spec(spec)
    assert isinstance(spec, dict)
    assert isinstance(spec["body"], rdflib.Graph)
    spec["name"] = "test"
    tl = TemplateLibrary.create("my_template_library")
    # no dependencies to resolve, so we can just throw this away
    _ = spec.pop("dependencies")
    spec["optional_args"] = spec.pop("optional", [])
    templ = tl.create_template(**spec)
    assert templ.name == "test"
    assert sorted(templ.parameters) == sorted(("name", "occ", "temp", "sp", "zone"))
    assert graph_size(templ.body) == 8
