from pathlib import Path

from rdflib import Namespace

from buildingmotif.monomorphism import TemplateMonomorphisms
from buildingmotif.namespaces import BRICK, RDF
from buildingmotif.template import Template, TemplateLibrary
from buildingmotif.utils import new_temporary_graph

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SMALL_OFFICE_BRICK_TTL = FIXTURES_DIR / "smallOffice_brick.ttl"

ONTOLOGY = new_temporary_graph()
ONTOLOGY.parse(FIXTURES_DIR / "Brick1.3rc1.ttl")


def test_simple_monomorphism():
    BLDG = Namespace("urn:bldg#")
    T = Template(
        None,
        name="temp",
        head=["room"],
        body="""
        {room} a brick:Room ;
            brick:isPartOf {floor} .
        {floor} a brick:Floor .""",
        deps={},
    )
    G = new_temporary_graph()
    G.bind("bldg", BLDG)

    G.add((BLDG.C, RDF.type, BRICK.Room))
    G.add((BLDG.C, BRICK.isPartOf, BLDG.D))
    G.add((BLDG.D, RDF.type, BRICK.Building))

    mms = TemplateMonomorphisms(G, T, ONTOLOGY)
    assert mms.largest_mapping_size == 2
    mapping = next(mms.mappings_iter())
    assert mapping is not None
    assert mapping[BLDG.C] == mms.template_bindings["room"]
    assert mapping[BRICK.Room] == BRICK.Room
    graph = mms.building_subgraph_from_mapping(mapping)
    assert graph is not None
    assert (BLDG.C, RDF.type, BRICK.Room) in graph
    remaining = mms.remaining_template(mapping)
    assert remaining is not None
    assert (mms.template_bindings["floor"], RDF.type, BRICK.Floor) in remaining
    assert (
        mms.template_bindings["room"],
        BRICK.isPartOf,
        mms.template_bindings["floor"],
    ) in remaining


def test_template_monomorphism():
    lib = TemplateLibrary(FIXTURES_DIR / "templates" / "smalloffice.yml")
    templ = lib["zone"][0]
    B = new_temporary_graph()
    B.parse(SMALL_OFFICE_BRICK_TTL)
    mms = TemplateMonomorphisms(B, templ, ONTOLOGY)
    mappings = [m for m in mms.mappings_iter() if len(m) == mms.largest_mapping_size]
    assert len(mappings) == 5, "Should have 5 template matchings"
    graphs = [mms.building_subgraph_from_mapping(m) for m in mappings]
    for mapping, graph in zip(mappings, graphs):
        leftover = mms.remaining_template(mapping)
        assert leftover is not None
