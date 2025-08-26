from rdflib import Graph, URIRef
from buildingmotif.namespaces import PARAM, RDF
from buildingmotif.api.views.model import _templates_payload_from_context


class DummyTemplate:
    def __init__(self, param_name: str, param_type_uri: str):
        self.parameters = {param_name: None}
        self.body = Graph()
        self.body.add((PARAM[param_name], RDF.type, URIRef(param_type_uri)))

    def inline_dependencies(self):
        # In these tests we don't model dependencies; return self.
        return self


class DummyCtx:
    def __init__(self, pairs):
        # pairs: List[Tuple[Optional[URIRef], DummyTemplate]]
        self._pairs = pairs

    def as_templates_with_focus(self):
        return self._pairs


def test_templates_payload_includes_focus_and_parameters():
    # Arrange: create two templates, one with a focus node and one graph-level (None)
    focus_uri = URIRef("urn:example:focus1")
    templ1 = DummyTemplate(param_name="p", param_type_uri="urn:example:ClassA")
    templ2 = DummyTemplate(param_name="q", param_type_uri="urn:example:ClassB")

    ctx = DummyCtx(pairs=[(focus_uri, templ1), (None, templ2)])

    # Act
    payload = _templates_payload_from_context(ctx)

    # Assert: two entries, each includes 'body', 'parameters', and 'focus'
    assert isinstance(payload, list) and len(payload) == 2

    first = payload[0]
    assert set(first.keys()) == {"body", "parameters", "focus"}
    assert first["focus"] == str(focus_uri)
    assert isinstance(first["body"], str) and "@prefix" in first["body"]
    assert first["parameters"] == [{"name": "p", "types": ["urn:example:ClassA"]}]

    second = payload[1]
    assert set(second.keys()) == {"body", "parameters", "focus"}
    assert second["focus"] is None
    assert isinstance(second["body"], str) and "@prefix" in second["body"]
    assert second["parameters"] == [{"name": "q", "types": ["urn:example:ClassB"]}]
