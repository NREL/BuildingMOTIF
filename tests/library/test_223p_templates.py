import os
from typing import Tuple

from rdflib import Graph, Namespace, URIRef

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library, Model
from buildingmotif.namespaces import RDF, S223, bind_prefixes
from tests.library.conftest import PatchBuildingMotif, instances

libraries = [
    "libraries/ashrae/223p/nrel-templates",
]


def setup_building_motif_s223() -> Tuple[BuildingMOTIF, Library]:
    with PatchBuildingMotif():
        os.environ["bmotif_module"] = __file__
        bm = BuildingMOTIF("sqlite://", shacl_engine="topquadrant")
        instances[__file__] = bm
        # bm = get_building_motif()
        bm.setup_tables()
        s223 = Library.load(
            ontology_graph="libraries/ashrae/223p/ontology/223p.ttl",
            run_shacl_inference=False,
        )
        bm.session.commit()
        return bm, s223


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


def test_223p_template(bm, s223, library, template):
    # set the module to this file; this helps the monkeypatch determine which BuildingMOTIF instance to use
    with PatchBuildingMotif():
        os.environ["bmotif_module"] = __file__
        try:
            MODEL = Namespace("urn:ex/")
            m = Model.create(MODEL)
            _, g = template.inline_dependencies().fill(MODEL, include_optional=False)
            assert isinstance(g, Graph), "was not a graph"
            bind_prefixes(g)
            plug_223_connection_points(g)
            m.add_graph(g)
            ctx = m.validate(
                [s223.get_shape_collection()], error_on_missing_imports=False
            )
        except Exception as e:
            bm.session.rollback()
            raise e
        assert ctx.valid, ctx.report_string


def pytest_generate_tests(metafunc):
    # set the module to this file; this helps the monkeypatch determine which BuildingMOTIF instance to use
    os.environ["bmotif_module"] = __file__
    # setup building motif
    bm, s223 = setup_building_motif_s223()
    if "test_223p_template" == metafunc.function.__name__:
        params = []
        ids = []
        for library_name in libraries:
            with PatchBuildingMotif():
                library = Library.load(
                    directory=library_name,
                    run_shacl_inference=False,
                    infer_templates=False,
                )
                templates = library.get_templates()
                params.extend([(bm, s223, library, template) for template in templates])
                ids.extend(
                    [f"{library.name}-{template.name}" for template in templates]
                )
        metafunc.parametrize("bm,s223,library,template", params, ids=ids)
