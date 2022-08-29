import pytest
import rdflib
from rdflib import RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import FOAF
from sqlalchemy.exc import IntegrityError, NoResultFound

from buildingmotif.dataclasses import Library, Template
from buildingmotif.dataclasses.template import Dependency
from buildingmotif.template_compilation import compile_template_spec
from buildingmotif.utils import graph_size


def test_create(clean_building_motif):
    lib = Library.create("my_library")
    t = lib.create_template("my_template")

    assert isinstance(t, Template)
    assert isinstance(t.id, int)
    assert t.name == "my_template"
    assert isinstance(t.body, rdflib.Graph)
    assert t.defining_library == lib

    also_t = lib.get_templates()[0]
    assert also_t.id == t.id
    assert also_t.name == t.name
    assert isomorphic(also_t.body, t.body)
    assert also_t.defining_library == lib


def test_load(clean_building_motif):
    lib = Library.create("my_library")
    t = lib.create_template("my_template")
    t.body.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))

    result = Template.load(t.id)
    assert result.id == t.id
    assert result.name == t.name
    assert isomorphic(result.body, t.body)


def test_set_name(clean_building_motif):
    lib = Library.create("my_library")
    t = lib.create_template("my_template")

    t.name = "new name"
    assert t.name == "new name"


def test_update_id(clean_building_motif):
    lib = Library.create("my_library")
    t = lib.create_template("my_template")

    with pytest.raises(AttributeError):
        t.id = 1


def test_save_body(clean_building_motif):
    lib = Library.create("my_library")
    t = lib.create_template("my_template")

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
    lib = Library.create("my_library")
    dependant = lib.create_template("dependant")
    dependee = lib.create_template("dependee")

    dependant.add_dependency(dependee, {"name": "1", "param": "2"})

    assert dependant.get_dependencies() == (
        Dependency(dependee.id, {"name": "1", "param": "2"}),
    )


def test_add_dependency_bad_args(clean_building_motif):
    lib = Library.create("my_library")
    dependant = lib.create_template("dependant")
    dependee = lib.create_template("dependee")

    with pytest.raises(ValueError):
        dependant.add_dependency(dependee, {"bad": "xyz"})


def test_add_dependency_already_exist(clean_building_motif):
    lib = Library.create("my_library")
    dependant = lib.create_template("dependant")
    dependee = lib.create_template("dependee")

    dependant.add_dependency(dependee, {"name": "1", "param": "2"})

    with pytest.raises(IntegrityError):
        dependant.add_dependency(dependee, {"name": "1", "param": "2"})

    clean_building_motif.session.rollback()


def test_get_dependencies(clean_building_motif):
    lib = Library.create("my_library")
    dependant = lib.create_template("dependant")
    dependee = lib.create_template("dependee")

    dependant.add_dependency(dependee, {"name": "1", "param": "2"})

    assert dependant.get_dependencies() == (
        Dependency(dependee.id, {"name": "1", "param": "2"}),
    )


def test_remove_dependency(clean_building_motif):
    lib = Library.create("my_library")
    dependant = lib.create_template("dependant")
    dependee = lib.create_template("dependee")

    dependant.add_dependency(dependee, {"name": "1", "param": "2"})
    assert dependant.get_dependencies() == (
        Dependency(dependee.id, {"name": "1", "param": "2"}),
    )

    dependant.remove_dependency(dependee)
    assert dependant.get_dependencies() == ()


def test_remove_depedancy_does_not_exist(clean_building_motif):
    lib = Library.create("my_library")
    dependant = lib.create_template("dependant")
    dependee = lib.create_template("dependee")

    with pytest.raises(NoResultFound):
        dependant.remove_dependency(dependee)

    clean_building_motif.session.rollback()


def test_get_library_dependencies(clean_building_motif):
    Library.load(ontology_graph="tests/unit/fixtures/Brick1.3rc1-equip-only.ttl")
    lib = Library.load(directory="tests/unit/fixtures/sample-lib-1")
    sf_templ = lib.get_template_by_name("fan")
    libs = sf_templ.library_dependencies()
    assert len(libs) == 2
    assert all(map(lambda x: isinstance(x, Library), libs))
    assert {str(lib.name) for lib in libs} == {
        "sample-lib-1",
        "https://brickschema.org/schema/1.3/Brick",
    }


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
    lib = Library.create("my_library")
    # no dependencies to resolve, so we can just throw this away
    _ = spec.pop("dependencies")
    spec["optional_args"] = spec.pop("optional", [])
    templ = lib.create_template(**spec)
    assert templ.name == "test"
    assert sorted(templ.parameters) == sorted(("name", "occ", "temp", "sp", "zone"))
    assert graph_size(templ.body) == 8
