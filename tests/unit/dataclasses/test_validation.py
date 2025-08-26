from secrets import token_hex

import pytest
from rdflib import Namespace

from buildingmotif import get_building_motif
from buildingmotif.dataclasses import Library, Model
from buildingmotif.namespaces import BRICK, A


def test_as_templates_name_collision_raises(clean_building_motif, shacl_engine):
    # Configure SHACL engine
    bm = get_building_motif()
    bm.shacl_engine = shacl_engine

    # Load libraries used for validation (Brick ontology + some shapes files that reference each other and Brick)
    brick = Library.load(ontology_graph="tests/unit/fixtures/Brick.ttl")
    shape1 = Library.load(ontology_graph="tests/unit/fixtures/shapes/shape1.ttl")
    shape3 = Library.load(ontology_graph="tests/unit/fixtures/shapes/shape3.ttl")

    # Build a minimal model with a AHU missing required sensors + VAVs
    BLDG = Namespace("urn:building/")
    model = Model.create(name=BLDG)
    model.add_triples((BLDG["ahu1"], A, BRICK.Air_Handling_Unit))

    # Create another library that contains templates with the same names that
    # diffset_to_templates will generate for the missing pieces on vav1.
    # This reproduces the global name-only lookup collision during inlining.
    evil_lib = Library.create(f"evil_lib_{token_hex(4)}")
    evil_lib.create_template("resolveahu1vav_shape_1")

    # Compile against the shapes and validate to produce a ValidationContext
    compiled = model.compile(
        [
            shape1.get_shape_collection(),
            shape3.get_shape_collection(),
            brick.get_shape_collection(),
        ]
    )
    ctx = compiled.validate()
    assert ctx is not None
    assert not ctx.valid

    # Calling as_templates should attempt to inline dependencies, which could
    # trigger a name-only lookup collision and raise a ValueError complaining
    # that the template is not in the resolve_* library.
    t = ctx.as_templates()
    assert len(t) == 1, f"Expected 1 template, got {len(t)}"
