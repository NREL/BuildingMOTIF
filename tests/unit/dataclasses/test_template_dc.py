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
    t = tl.create_template("my_template", head=["ding", "dong"])

    assert isinstance(t, Template)
    assert isinstance(t.id, int)
    assert t.name == "my_template"
    assert t.head == ("ding", "dong")
    assert isinstance(t.body, rdflib.Graph)

    also_t = tl.get_templates()[0]
    assert also_t.id == t.id
    assert also_t.name == t.name
    assert also_t.head == ("ding", "dong")
    assert isomorphic(also_t.body, t.body)


def test_load(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template", head=["ding", "dong"])
    t.body.add((URIRef("http://example.org/alex"), RDF.type, FOAF.Person))

    result = Template.load(t.id)
    assert result.id == t.id
    assert result.name == t.name
    assert result.head == ("ding", "dong")
    assert isomorphic(result.body, t.body)


def test_set_name(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template", head=[])

    t.name = "new name"
    assert t.name == "new name"


def test_update_id(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template", head=[])

    with pytest.raises(AttributeError):
        t.id = 1


def test_update_head(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template", head=[])

    with pytest.raises(AttributeError):
        t.head = ["ding", "dong"]


def test_save_body(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    t = tl.create_template("my_template", head=[])

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
    dependant = tl.create_template("dependant", head=[])
    dependee = tl.create_template("dependee", head=["ding", "dong"])

    dependant.add_dependency(dependee, {"ding": "1", "dong": "2"})

    assert dependant.get_dependencies() == (
        Dependency(dependee.id, {"ding": "1", "dong": "2"}),
    )


def test_add_dependency_bad_args(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant", head=[])
    dependee = tl.create_template("dependee", head=["ding", "dong"])

    with pytest.raises(ValueError):
        dependant.add_dependency(dependee, {})


def test_add_dependency_already_exist(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant", head=[])
    dependee = tl.create_template("dependee", head=["ding", "dong"])

    dependant.add_dependency(dependee, {"ding": "1", "dong": "2"})

    with pytest.raises(IntegrityError):
        dependant.add_dependency(dependee, {"ding": "1", "dong": "2"})

    clean_building_motif.session.rollback()


def test_get_dependencies(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant", head=[])
    dependee = tl.create_template("dependee", head=["ding", "dong"])

    dependant.add_dependency(dependee, {"ding": "1", "dong": "2"})

    assert dependant.get_dependencies() == (
        Dependency(dependee.id, {"ding": "1", "dong": "2"}),
    )


def test_remove_dependency(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant", head=[])
    dependee = tl.create_template("dependee", head=["ding", "dong"])

    dependant.add_dependency(dependee, {"ding": "1", "dong": "2"})
    assert dependant.get_dependencies() == (
        Dependency(dependee.id, {"ding": "1", "dong": "2"}),
    )

    dependant.remove_dependency(dependee)
    assert dependant.get_dependencies() == ()


def test_remove_depedancy_does_not_exist(clean_building_motif):
    tl = TemplateLibrary.create("my_template_library")
    dependant = tl.create_template("dependant", head=[])
    dependee = tl.create_template("dependee", head=["ding", "dong"])

    with pytest.raises(NoResultFound):
        dependant.remove_dependency(dependee)

    clean_building_motif.session.rollback()


def test_template_compilation(clean_building_motif):
    spec = {
        "head": ["name"],
        "hasPoint": {
            "occ": "https://brickschema.org/schema/Brick#Occupancy_Sensor",
            "temp": "https://brickschema.org/schema/Brick#Temperature_Sensor",
            "sp": "https://brickschema.org/schema/Brick#Temperature_Setpoint",
        },
        "downstream": {"zone": "https://brickschema.org/schema/Brick#HVAC_Zone"},
    }
    spec = compile_template_spec(spec)
    assert isinstance(spec, dict)
    assert spec["head"] == ["name"]
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
