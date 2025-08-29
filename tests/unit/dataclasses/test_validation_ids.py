from rdflib import Namespace

from buildingmotif import get_building_motif
from buildingmotif.dataclasses import Library, Model
from buildingmotif.namespaces import BRICK, A


def test_as_templates_returns_real_ids(clean_building_motif, shacl_engine):
    # Configure SHACL engine
    bm = get_building_motif()
    bm.shacl_engine = shacl_engine

    # Load libraries used for validation (Brick ontology + shapes)
    brick = Library.load(ontology_graph="tests/unit/fixtures/Brick.ttl")
    shape1 = Library.load(ontology_graph="tests/unit/fixtures/shapes/shape1.ttl")

    # Build a simple model with a VAV missing required sensors
    BLDG = Namespace("urn:building/")
    model = Model.create(name=BLDG)
    model.add_triples((BLDG["vav1"], A, BRICK.VAV))

    # Validate against shapes -> expect violations that yield templates
    ctx = model.validate([shape1.get_shape_collection(), brick.get_shape_collection()])
    assert ctx is not None
    assert not ctx.valid

    # Get inlined templates; IDs should be real DB IDs (positive), not ephemeral -1
    templates = ctx.as_templates()
    assert len(templates) >= 1
    assert all(isinstance(t.id, int) and t.id > 0 for t in templates)


def test_as_templates_with_focus_returns_real_ids(clean_building_motif, shacl_engine):
    # Configure SHACL engine
    bm = get_building_motif()
    bm.shacl_engine = shacl_engine

    # Load libraries used for validation (Brick ontology + shapes)
    brick = Library.load(ontology_graph="tests/unit/fixtures/Brick.ttl")
    shape1 = Library.load(ontology_graph="tests/unit/fixtures/shapes/shape1.ttl")

    # Build a simple model with a VAV missing required sensors
    BLDG = Namespace("urn:building/")
    model = Model.create(name=BLDG)
    model.add_triples((BLDG["vav1"], A, BRICK.VAV))

    # Validate against shapes -> expect violations that yield templates
    ctx = model.validate([shape1.get_shape_collection(), brick.get_shape_collection()])
    assert ctx is not None
    assert not ctx.valid

    # Get (focus, template) pairs and verify IDs are real (positive)
    templs_with_focus = ctx.as_templates_with_focus()
    assert len(templs_with_focus) >= 1
    for focus, templ in templs_with_focus:
        assert templ is not None
        assert isinstance(templ.id, int) and templ.id > 0
