import logging
import random
import string
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

import rdflib
from rdflib import RDF, RDFS, Graph, URIRef
from rdflib.paths import ZeroOrMore, ZeroOrOne
from rdflib.term import Node

from buildingmotif import get_building_motif
from buildingmotif.namespaces import BMOTIF, OWL, SH
from buildingmotif.utils import Triple, copy_graph

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF

ONTOLOGY_FILE = (
    Path(__file__).resolve().parents[1] / "resources" / "building_motif_ontology.ttl"
)
ontology = rdflib.Graph().parse(ONTOLOGY_FILE)


@dataclass
class ShapeCollection:
    """This class mirrors :py:class:`database.tables.DBShapeCollection`."""

    _id: int
    graph: rdflib.Graph
    _bm: "BuildingMOTIF"

    @classmethod
    def create(cls) -> "ShapeCollection":
        """Create a new ShapeCollection.

        :return: new ShapeCollection
        :rtype: ShapeCollection
        """
        bm = get_building_motif()
        db_shape_collection = bm.table_connection.create_db_shape_collection()
        graph = bm.graph_connection.create_graph(
            db_shape_collection.graph_id, rdflib.Graph()
        )

        return cls(_id=db_shape_collection.id, graph=graph, _bm=bm)

    @classmethod
    def load(cls, id: int) -> "ShapeCollection":
        """Get ShapeCollection from database by id.

        :param id: ShapeCollection id
        :type id: int
        :return: ShapeCollection
        :rtype: ShapeCollection
        """
        bm = get_building_motif()
        db_shape_collection = bm.table_connection.get_db_shape_collection(id)
        graph = bm.graph_connection.get_graph(db_shape_collection.graph_id)

        return cls(_id=db_shape_collection.id, graph=graph, _bm=bm)

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, new_id):
        raise AttributeError("Cannot modify db id")

    @property
    def graph_name(self) -> Optional[URIRef]:
        """
        Returns the name of the graph (subject of "a owl:Ontology")
        if one exists
        """
        # will be None if this is not found
        return self.graph.value(predicate=RDF.type, object=OWL.Ontology)  # type: ignore

    def add_triples(self, *triples: Triple) -> None:
        """Add the given triples to the graph.

        :param triples: a sequence of triples to add to the graph
        :type triples: Triple
        """
        for triple in triples:
            self.graph.add(triple)

    def add_graph(self, graph: rdflib.Graph) -> None:
        """Add the given graph to the ShapeCollection.

        :param graph: the graph to add to the ShapeCollection
        :type graph: rdflib.Graph
        """
        self.graph += graph

    def _cbd(self, shape_name, self_contained=True):
        """Retrieves the Concise Bounded Description (CBD) of the shape."""
        cbd = self.graph.cbd(shape_name)
        # if computing self-contained, do the fixed-point computation produced by unioning
        # the CBDs of all nodes in the current CBD until the graph does not change
        changed = True
        while self_contained and changed:
            new_g = rdflib.Graph()
            for node in cbd.all_nodes():
                new_g += self.graph.cbd(node)
            new_cbd = new_g + cbd
            changed = len(new_cbd) > cbd
            cbd = new_cbd
        return cbd

    def resolve_imports(
        self, recursive_limit: int = -1, error_on_missing_imports: bool = True
    ) -> "ShapeCollection":
        """Resolves `owl:imports` to as many levels as requested.

        By default, all `owl:imports` are recursively resolved. This limit can
        be changed to 0 to suppress resolving imports, or to 1..n to handle
        recursion up to that limit.

        :param recursive_limit: how many levels of `owl:imports` to resolve,
            defaults to -1 (all)
        :type recursive_limit: int, optional
        :param error_on_missing_imports: if True, raises an error if any of the dependency
            ontologies are missing (i.e. they need to be loaded into BuildingMOTIF), defaults
            to True
        :type error_on_missing_imports: bool, optional
        :return: a new ShapeCollection with the types resolved
        :rtype: ShapeCollection
        """
        resolved_namespaces: Set[rdflib.URIRef] = set()
        resolved = _resolve_imports(
            self.graph,
            recursive_limit,
            resolved_namespaces,
            error_on_missing_imports=error_on_missing_imports,
        )
        new_sc = ShapeCollection.create()
        new_sc.add_graph(resolved)
        return new_sc

    @classmethod
    def _get_subclasses_of_definition_type(
        cls, definition_type: URIRef
    ) -> List[URIRef]:
        """Get all the definition types in the ontology that are subclasses in
        the given definition types.

        :param definition_type: the given definition type
        :type definition_type: URIRef
        :return: list of included definition types
        :rtype: List[URIRef]
        """
        children = ontology.subjects(RDFS.subClassOf, definition_type)

        results = [definition_type]
        for child in children:
            results += cls._get_subclasses_of_definition_type(child)

        return results

    @classmethod
    def _get_included_domains(cls, domain: URIRef) -> List[URIRef]:
        """Get all the domains in the ontology that are included in the given
        domains.

        :param domain: the given domain
        :type domain: URIRef
        :return: list of included domains
        :rtype: List[URIRef]
        """
        children = ontology.subjects(BMOTIF.includes, domain)

        results = [domain]
        for child in children:
            results += cls._get_included_domains(child)

        return results

    def get_shapes_of_definition_type(self, definition_type: URIRef) -> List[URIRef]:
        """Get subjects present in shape of the definition type.

        :param definition_type: desired definition type
        :type definition_type: URIRef
        :return: subjects
        :rtype: List[URIRef]
        """
        definition_types = self._get_subclasses_of_definition_type(definition_type)

        results = []
        for definition_type in definition_types:
            results += self.graph.subjects(RDF.type, definition_type)

        return results

    def get_shapes_of_domain(self, domain: URIRef) -> List[URIRef]:
        """Get subjects present in shape of domain type.

        :param domain: desired domain
        :type domain: URIRef
        :return: subjects
        :rtype: List[URIRef]
        """
        included_domains = self._get_included_domains(domain)

        results = []
        for domain in included_domains:
            results += self.graph.subjects(RDF.type, domain)

        return results

    def get_shapes_about_class(
        self, rdf_type: URIRef, contexts: Optional[List["ShapeCollection"]] = None
    ) -> List[URIRef]:
        """Returns a list of shapes that either target the given class (or
        superclasses of it), or otherwise only apply to URIs of the given type.

        :param rdf_type: an OWL class
        :type rdf_type: URIRef
        :param contexts: list of ShapeCollections that help determine the class
            structure
        :type contexts: List["ShapeCollection"], optional
        :return: a list of shapes in this ShapeCollection that concern that
            class
        :rtype: List[URIRef]
        """
        # merge the contexts together w/ our graph if they are provided, else
        # just use the existing shape collection graph
        if contexts is not None:
            context = sum(map(lambda x: x.graph, contexts), rdflib.Graph())
            graph = self.graph + context
        else:
            graph = self.graph
        rows = graph.query(
            f"""
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?shape WHERE {{
            ?shape a sh:NodeShape .
            {rdf_type.n3()} rdfs:subClassOf* ?class .
            {{ ?shape sh:targetClass ?class }}
            UNION
            {{ ?shape sh:class ?class }}
        }}"""
        )
        return [row[0] for row in rows]  # type: ignore

    def shape_to_query(self, shape: URIRef) -> str:
        """
        This method takes a URI representing a SHACL shape as an argument and returns
        a SPARQL query selecting the information which would be used to satisfy that
        SHACL shape. This uses the following rules:
        - `<shape> sh:targetClass <class>` -> `?target rdf:type/rdfs:subClassOf* <class>`
        - `<shape> sh:property [ sh:path <path>; sh:class <class>; sh:name <name> ]` ->
            ?target <path> ?name . ?name rdf:type/rdfs:subClassOf* <class>
        - `<shape> sh:property [ sh:path <path>; sh:hasValue <value>]` ->
            ?target <path> <value>
        """
        clauses, project = _shape_to_where(self.graph, shape)
        preamble = """PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        """
        return f"{preamble} SELECT {' '.join(project)} WHERE {{\n{clauses}\n}}"


def _is_list(graph: Graph, node: Node):
    return (node, RDF.first, None) in graph


def _sh_path_to_path(graph: Graph, sh_path_value: Node):
    # check if sh:path points to a list
    if _is_list(graph, sh_path_value):
        components = list(
            graph.objects(sh_path_value, (RDF.rest * ZeroOrMore) / RDF.first)  # type: ignore
        )
        return "/".join([_sh_path_to_path(graph, comp) for comp in components])
    part = graph.value(sh_path_value, SH.oneOrMorePath)
    if part is not None:
        return f"{_sh_path_to_path(graph, part)}+"
    part = graph.value(sh_path_value, SH.zeroOrMorePath)
    if part is not None:
        return f"{_sh_path_to_path(graph, part)}*"
    part = graph.value(sh_path_value, SH.zeroOrOnePath)
    if part is not None:
        return f"{_sh_path_to_path(graph, part)}?"
    return sh_path_value.n3()


def _shape_to_where(graph: Graph, shape: URIRef) -> Tuple[str, List[str]]:
    # we will build the query as a string
    clauses: str = ""
    # build up the SELECT clause as a set of vars
    project: Set[str] = {"?target"}

    # local state for generating unique variable names
    prefix = "".join(random.choice(string.ascii_lowercase) for _ in range(2))
    variable_counter = 0

    def gensym():
        nonlocal variable_counter
        varname = f"{prefix}{variable_counter}"
        variable_counter += 1
        return varname

    # `<shape> sh:targetClass <class>` -> `?target rdf:type/rdfs:subClassOf* <class>`
    targetClasses = graph.objects(shape, SH.targetClass | SH["class"])
    tc_clauses = [
        f"?target rdf:type/rdfs:subClassOf* {tc.n3()} .\n" for tc in targetClasses  # type: ignore
    ]
    clauses += " UNION ".join(tc_clauses)

    # find all of the non-qualified property shapes. All of these will use the same variable
    # for all uses of the same sh:path value
    pshapes_by_path: Dict[Node, List[Node]] = defaultdict(list)
    for pshape in graph.objects(shape, SH.property):
        path = _sh_path_to_path(graph, graph.value(pshape, SH.path))
        if not graph.value(pshape, SH.qualifiedValueShape):
            pshapes_by_path[path].append(pshape)  # type: ignore

    for dep_shape in graph.objects(shape, SH.node):
        dep_clause, dep_project = _shape_to_where(graph, dep_shape)
        clauses += dep_clause
        project.update(dep_project)

    for or_clause in graph.objects(shape, SH["or"]):
        items = list(graph.objects(or_clause, (RDF.rest * ZeroOrMore) / RDF.first))  # type: ignore
        or_parts = []
        for item in items:
            or_body, or_project = _shape_to_where(graph, item)
            or_parts.append(or_body)
            project.update(or_project)
        clauses += " UNION ".join(f"{{ {or_body} }}" for or_body in or_parts)

    # assign a unique variable for each sh:path w/o a qualified shape
    pshape_vars: Dict[Node, str] = {}
    for pshape_list in pshapes_by_path.values():
        varname = f"?{gensym()}"
        for pshape in pshape_list:
            pshape_vars[pshape] = varname

    for pshape in graph.objects(shape, SH.property):
        # get the varname if we've already assigned one for this pshape above,
        # or generate a new one. When generating a name, use the SH.name field
        # in the PropertyShape or generate a unique one
        name = pshape_vars.get(
            pshape, f"?{graph.value(pshape, SH.name) or gensym()}".replace(" ", "_")
        )
        path = _sh_path_to_path(graph, graph.value(pshape, SH.path))
        qMinCount = graph.value(pshape, SH.qualifiedMinCount) or 0

        pclass = graph.value(
            pshape, (SH["qualifiedValueShape"] * ZeroOrOne / SH["class"])  # type: ignore
        )
        if pclass:
            clause = f"?target {path} {name} .\n {name} rdf:type/rdfs:subClassOf* {pclass.n3()} .\n"
            if qMinCount == 0:
                clause = f"OPTIONAL {{ {clause} }} .\n"
            clauses += clause
            project.add(name)

        pnode = graph.value(
            pshape, (SH["qualifiedValueShape"] * ZeroOrOne / SH["node"])  # type: ignore
        )
        if pnode:
            node_clauses, node_project = _shape_to_where(graph, pnode)
            clause = f"?target {path} {name} .\n"
            clause += node_clauses.replace("?target", name)
            if qMinCount == 0:
                clause = f"OPTIONAL {{ {clause} }}"
            clauses += clause
            project.update({p.replace("?target", name) for p in node_project})

        or_values = graph.value(
            pshape, (SH["qualifiedValueShape"] * ZeroOrOne / SH["or"])
        )
        if or_values:
            items = list(graph.objects(or_values, (RDF.rest * ZeroOrMore) / RDF.first))
            or_parts = []
            for item in items:
                or_body, or_project = _shape_to_where(graph, item)
                or_parts.append(or_body)
                project.update(or_project)
            clauses += " UNION ".join(f"{{ {or_body} }}" for or_body in or_parts)

        pvalue = graph.value(pshape, SH.hasValue)
        if pvalue:
            clauses += f"?target {path} {pvalue.n3()} .\n"

    return clauses, list(project)


def _resolve_imports(
    graph: rdflib.Graph,
    recursive_limit: int,
    seen: Set[rdflib.URIRef],
    error_on_missing_imports: bool = True,
) -> rdflib.Graph:
    from buildingmotif.dataclasses.library import Library

    bm = get_building_motif()

    logger = logging.getLogger(__name__)

    if recursive_limit == 0:
        return graph
    new_g = copy_graph(graph)
    for ontology in graph.objects(predicate=OWL.imports):
        if ontology in seen:
            continue
        seen.add(ontology)

        # go find the graph definition from our libraries
        try:
            lib = Library.load(name=ontology)
            sc_to_add = lib.get_shape_collection()
        except Exception as e:
            logger.warning(
                "Could not resolve import of %s from Libraries (%s). Trying shape collections",
                ontology,
                e,
            )
            sc_to_add = None

        # search through our shape collections for a graph with the provided name
        if sc_to_add is None:
            for shape_collection in bm.table_connection.get_all_db_shape_collections():
                sc = ShapeCollection.load(shape_collection.id)
                if sc.graph_name == ontology:
                    sc_to_add = sc
                    break
            logger.warning(
                "Could not resolve import of %s from Libraries. Trying shape collections",
                ontology,
            )

        if sc_to_add is None:
            if error_on_missing_imports:
                raise Exception("Could not resolve import of %s", ontology)
            continue

        dependency = _resolve_imports(
            sc_to_add.graph,
            recursive_limit - 1,
            seen,
            error_on_missing_imports=error_on_missing_imports,
        )
        new_g += dependency
    return new_g
