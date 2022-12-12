from pathlib import Path

import pytest
from rdflib import Graph, Namespace

from buildingmotif.dataclasses import Library, Model


@pytest.mark.integration
@pytest.mark.xfail(
    reason="223P templates should be brought up to date with recent changes in the standard"
)
def test_223p_library(bm, library_path_223p: Path):
    ont_223p = Library.load(ontology_graph="libraries/ashrae/223p/ontology/223p.ttl")
    lib = Library.load(directory=str(library_path_223p))
    bm.session.commit()

    MODEL = Namespace("urn:ex/")
    for templ in lib.get_templates():
        print(templ.name)
        m = Model.create(MODEL)
        _, g = templ.inline_dependencies().fill(MODEL)
        assert isinstance(g, Graph), "was not a graph"
        m.add_graph(g)
        ctx = m.validate([ont_223p.get_shape_collection()])
        assert ctx.valid, ctx.report_string
        bm.session.rollback()
