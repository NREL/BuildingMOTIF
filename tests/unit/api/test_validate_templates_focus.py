import pytest
from rdflib import Graph, URIRef

from buildingmotif.api.views import model as model_views


class FakeTemplate:
    def __init__(self):
        # Minimal template double: empty body and no parameters
        self.body = Graph()
        self.parameters = set()

    def inline_dependencies(self):
        # The validate endpoint helper inlines then reads .body and .parameters
        return self


class FakeCtx:
    def __init__(self, pairs):
        # pairs is a list of (focus, template) tuples
        self._pairs = pairs

    def as_templates_with_focus(self):
        return self._pairs


def test_templates_payload_includes_focus():
    templ_with_focus = FakeTemplate()
    templ_graph_level = FakeTemplate()

    ctx = FakeCtx(
        [
            (URIRef("urn:test:focus-node"), templ_with_focus),
            (None, templ_graph_level),
        ]
    )

    payload = model_views._templates_payload_from_context(ctx)

    assert isinstance(payload, list)
    assert len(payload) == 2

    # Ensure every template dict has a 'focus' key
    assert all("focus" in item for item in payload)

    foci = {item["focus"] for item in payload}
    # One item should include the stringified focus node
    assert "urn:test:focus-node" in foci
    # One item should explicitly include None for graph-level templates
    assert None in foci
