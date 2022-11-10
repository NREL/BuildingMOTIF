from typing import List, Optional, Tuple, Union

from rdflib import RDF, BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.term import Node

from buildingmotif.namespaces import SH, A, bind_prefixes


class Shape(Graph):
    def __init__(
        self,
        identifier: Optional[Union[Node, str]] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(identifier=identifier)
        bind_prefixes(self)

        if message:
            self.add((self.identifier, SH["message"], Literal(message)))

    def add_property(self, property: URIRef, object: Node):
        self.add((self, property, object))

        return self

    def add_list_property(
        self, property: URIRef, nodes: Union[List[Node], Tuple[Node, ...]]
    ):
        identifier = BNode()
        Collection(self, identifier, nodes)

        self.add((self, property, identifier))

        return self

    def OR(self, *nodes: Node):
        self.add_list_property(SH["or"], nodes)
        return self

    def AND(self, *nodes: Node):
        self.add_list_property(SH["and"], nodes)
        return self

    def NOT(self, node: Node):
        self.add((self, SH["not"], node))

        return self

    def XONE(self, *nodes: Node):
        self.add_list_property(SH["xone"], nodes)
        return self

    def add(self, triple: Tuple[Node, Node, Node]):
        (s, p, o) = triple
        if isinstance(o, Shape):
            self += o
            o = o.identifier
        if s == self:
            s = s.identifier
        triple = (s, p, o)
        return super().add(triple)


class NodeShape(Shape):
    def __init__(
        self,
        identifier: Optional[Union[Node, str]] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(identifier=identifier, message=message)

        self.add((self, A, SH["NodeShape"]))

    def of_class(self, class_: Node, target=False):
        predicate = SH["class"]
        if target:
            predicate = SH["target_class"]

        self.add((self, predicate, class_))

        return self

    def has_property(self, property: Node = None):
        if isinstance(property, URIRef):
            property = PropertyShape().has_path(property)

        self.add((self, SH["property"], property))

        return self


class PropertyShape(Shape):
    def __init__(
        self,
        identifier: Optional[Union[Node, str]] = None,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(identifier=identifier, message=message)

        self.add((self, RDF.type, SH["PropertyShape"]))

    def has_path(
        self,
        path: Node,
        zero_or_one: bool = False,
        zero_or_more: bool = False,
        one_or_more: bool = False,
    ) -> "PropertyShape":

        if zero_or_one or zero_or_more or one_or_more:
            path_constraint = None
            if zero_or_one:
                path_constraint = SH["path-zero-or-one"]
            elif zero_or_more:
                path_constraint = SH["path-zero-or-more"]
            elif one_or_more:
                path_constraint = SH["path-one-or-more"]
            self.add((self, SH["path"], Shape().add_property(path_constraint, path)))
        else:
            self.add((self, SH["path"], path))

        return self

    def matches_class(
        self, class_: URIRef, min: int = None, max: int = None, exactly: int = None
    ):
        self.add((self, SH["class"], class_))

        if exactly is not None:
            min = max = exactly
        if min is not None:
            self.add((self, SH["minCount"], Literal(min)))
        if max is not None:
            self.add((self, SH["maxCount"], Literal(max)))
        return self

    def matches_shape(
        self, shape: Node, min: int = None, max: int = None, exactly: int = None
    ):
        if min is None and max is None and exactly is None:
            self.add((self, SH["node"], shape))
            return self

        self.add((self, SH["qualifiedValueShape"], shape))
        if exactly is not None:
            min = max = exactly
        if min is not None:
            self.add((self, SH["qualifiedMinCount"], Literal(min)))
        if max is not None:
            self.add((self, SH["qualifiedMaxCount"], Literal(max)))
        return self


def OR(*nodes: Node) -> Shape:
    return Shape().OR(*nodes)


def AND(*nodes: Node) -> Shape:
    return Shape().AND(*nodes)


def NOT(node: Node) -> Shape:
    return Shape().NOT(node)


def XONE(*nodes: Node) -> Shape:
    return Shape().XONE(*nodes)
