from pathlib import Path
from typing import Set

import pytest
from rdflib import Graph, Namespace, URIRef

from buildingmotif.dataclasses import Library, Model
from buildingmotif.namespaces import RDF, S223, bind_prefixes

# these are templates that are difficult to test individually
# but are covered indirectly by other tests
S223_SKIP_TEMPLATES: Set[str] = {
    "sensor",
    "differential-sensor",
    "air-outlet-cp",
    "air-inlet-cp",
    "water-outlet-cp",
    "water-inlet-cp",
    "duct",
}


def plug_223_connection_points(g: Graph):
    """
    223P models won't validate if they have unconnected connection points.
    This function creates a basic s223:Equipment for each unconnected connection point
    and connects them to the connection point.
    """
    query = """
    PREFIX s223: <http://data.ashrae.org/standard223#>
    SELECT ?cp WHERE {
        { ?cp rdf:type s223:OutletConnectionPoint }
        UNION
        { ?cp rdf:type s223:InletConnectionPoint }
        UNION
        { ?cp rdf:type s223:BidirectionalConnectionPoint }
        FILTER NOT EXISTS {
            ?cp s223:cnx ?x
        }
        FILTER NOT EXISTS {
            ?y s223:hasConnectionPoint ?x
        }
    }"""
    for row in g.query(query):
        cp = row[0]
        e = URIRef(f"urn:__plug__/{str(cp)[-8:]}")
        g.add((cp, S223.cnx, e))
        g.add((e, RDF.type, S223.Connectable))


@pytest.mark.integration
def test_brick_library(bm, library_path_brick: Path):
    Library.load(ontology_graph="libraries/brick/Brick.ttl")
    Library.load(directory=str(library_path_brick))
    bm.session.commit()


@pytest.mark.integration
def test_223p_library(bm, library_path_223p: Path):
    Library.load(ontology_graph="libraries/ashrae/223p/ontology/223p.ttl")
    Library.load(directory=str(library_path_223p))
    bm.session.commit()


@pytest.mark.integration
def test_223p_template(bm, library_path_223p, template_223p, shacl_engine):
    bm.shacl_engine = shacl_engine
    ont_223p = Library.load(ontology_graph="libraries/ashrae/223p/ontology/223p.ttl")

    # pyshacl evaluation takes a long time, so we only test a couple of templates
    # from specific libraries
    use_pyshacl = {
        "nrel-templates": {
            "damper",
            "makeup-air-unit",
        }
    }
    if shacl_engine == "pyshacl" and library_path_223p in use_pyshacl:
        if template_223p not in use_pyshacl[library_path_223p]:
            pytest.skip("pyshacl evaluation is slow, skipping this template")

    lib = Library.load(directory=str(library_path_223p))

    template_223p = lib.get_template_by_name(template_223p)

    MODEL = Namespace("urn:ex/")
    m = Model.create(MODEL)
    _, g = template_223p.inline_dependencies().fill(MODEL, include_optional=False)
    assert isinstance(g, Graph), "was not a graph"
    bind_prefixes(g)
    plug_223_connection_points(g)
    m.add_graph(g)
    m.graph.serialize("/tmp/model.ttl")
    ctx = m.validate(
        [
            ont_223p.get_shape_collection(),
        ],
        error_on_missing_imports=False,
    )
    ctx.report.serialize("/tmp/report.ttl")
    assert ctx.valid, ctx.report_string


@pytest.mark.integration
def test_brick_template(bm, library_path_brick, template_brick, shacl_engine):
    bm.shacl_engine = shacl_engine
    ont_brick = Library.load(ontology_graph="libraries/brick/Brick.ttl")

    lib = Library.load(directory=str(library_path_brick))

    template_brick = lib.get_template_by_name(template_brick)

    MODEL = Namespace("urn:ex/")
    m = Model.create(MODEL)
    _, g = template_brick.inline_dependencies().fill(MODEL, include_optional=False)
    assert isinstance(g, Graph), "was not a graph"
    bind_prefixes(g)
    m.add_graph(g)
    m.graph.serialize("/tmp/model.ttl")
    ctx = m.validate([ont_brick.get_shape_collection()])
    ctx.report.serialize("/tmp/report.ttl")
    assert ctx.valid, ctx.report_string
