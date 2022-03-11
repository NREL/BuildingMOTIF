from pathlib import Path

from rdflib import Namespace

from buildingmotif.monomorphism import TemplateMonomorphisms
from buildingmotif.namespaces import BRICK, RDF
from buildingmotif.template import TemplateLibrary
from buildingmotif.utils import new_temporary_graph

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SMALL_OFFICE_BRICK_TTL = FIXTURES_DIR / "smallOffice_brick.ttl"

ONTOLOGY = new_temporary_graph()
ONTOLOGY.parse(FIXTURES_DIR / "Brick1.3rc1.ttl")


def test_simple_monomorphism():
    BLDG = Namespace("urn:bldg#")
    T = new_temporary_graph()
    T.bind("bldg", BLDG)
    G = new_temporary_graph()
    G.bind("bldg", BLDG)

    T.add((BLDG.A, RDF.type, BRICK.Room))
    T.add((BLDG.A, BRICK.isPartOf, BLDG.B))
    T.add((BLDG.B, RDF.type, BRICK.Floor))

    G.add((BLDG.C, RDF.type, BRICK.Room))
    G.add((BLDG.C, BRICK.isPartOf, BLDG.D))
    G.add((BLDG.D, RDF.type, BRICK.Building))

    mms = TemplateMonomorphisms(G, T, ONTOLOGY)
    assert mms.largest_mapping_size == 2
    mapping = next(mms.mappings_iter())
    assert mapping is not None
    assert mapping[BLDG.C] == BLDG.A
    assert mapping[BRICK.Room] == BRICK.Room
    graph = mms.building_subgraph_from_mapping(mapping)
    assert graph is not None
    assert (BLDG.C, RDF.type, BRICK.Room) in graph
    remaining = mms.remaining_template(mapping)
    assert remaining is not None
    assert (BLDG.B, RDF.type, BRICK.Floor) in remaining


def test_template_monomorphism():
    BLDG = Namespace("urn:bldg#")
    lib = TemplateLibrary(FIXTURES_DIR / "templates" / "smalloffice.yml")
    templ = lib["zone"][0]
    T = templ.fill_in(BLDG)
    print(T.serialize(format="turtle"))
    B = new_temporary_graph()
    B.parse(SMALL_OFFICE_BRICK_TTL)
    mms = TemplateMonomorphisms(B, T, ONTOLOGY)
    mappings = [m for m in mms.mappings_iter() if len(m) == mms.largest_mapping_size]
    assert len(mappings) == 5, "Should have 5 template matchings"
    graphs = [mms.building_subgraph_from_mapping(m) for m in mappings]
    for mapping, graph in zip(mappings, graphs):
        leftover = mms.remaining_template(mapping)
        assert leftover is not None
