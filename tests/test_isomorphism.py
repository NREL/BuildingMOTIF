from rdflib import Namespace

from buildingmotif.isomorphism import find_largest_subgraph_monomorphism
from buildingmotif.namespaces import BRICK, RDF
from buildingmotif.utils import new_temporary_graph


def test_simple_isomorphism():
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

    ontology = new_temporary_graph()
    ontology.parse("https://sparql.gtf.fyi/ttl/Brick1.3rc1.ttl")
    mapping, tsub = find_largest_subgraph_monomorphism(T, G, ontology)
    assert len(mapping) == 3
    assert tsub is not None
    print(mapping)
    print(tsub.serialize(format="turtle"))
    assert (BLDG.A, RDF.type, BRICK.Room) in tsub
    assert (BLDG.A, BRICK.isPartOf, BLDG.B) in tsub
    assert len(tsub) == 2
