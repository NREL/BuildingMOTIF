import pytest
from secrets import token_hex
from rdflib import Namespace

from buildingmotif.dataclasses import Library, Model
from buildingmotif.namespaces import BRICK, A


def test_as_templates_name_collision_raises(building_motif, shacl_engine):
    # Configure SHACL engine
    building_motif.shacl_engine = shacl_engine

    # Load libraries used for validation (Brick ontology + a simple shapes file)
    brick = Library.load(ontology_graph="tests/unit/fixtures/Brick.ttl")
    shapes = Library.load(ontology_graph="tests/unit/fixtures/shapes/shape1.ttl")

    # Build a minimal model with a VAV missing required sensors
    BLDG = Namespace("urn:building/")
    model = Model.create(name=BLDG)
    model.add_triples((BLDG["vav1"], A, BRICK.VAV))

    # Create another library that contains templates with the same names that
    # diffset_to_templates will generate for the missing pieces on vav1.
    # This reproduces the global name-only lookup collision during inlining.
    evil_lib = Library.create(f"evil_lib_{token_hex(4)}")
    evil_lib.create_template("resolvevav1Temperature_Sensor")
    evil_lib.create_template("resolvevav1Air_Flow_Sensor")

    # Compile against the shapes and validate to produce a ValidationContext
    compiled = model.compile([shapes.get_shape_collection(), brick.get_shape_collection()])
    ctx = compiled.validate()
    assert ctx is not None
    assert not ctx.valid

    # Calling as_templates should attempt to inline dependencies, which will
    # trigger a name-only lookup collision and raise a ValueError complaining
    # that the template is not in the resolve_* library.
    with pytest.raises(ValueError) as excinfo:
        ctx.as_templates()
    assert "not in library" in str(excinfo.value)
