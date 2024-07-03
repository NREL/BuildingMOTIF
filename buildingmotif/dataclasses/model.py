from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

import rdflib
import rfc3987
from rdflib import URIRef

from buildingmotif import get_building_motif
from buildingmotif.dataclasses.shape_collection import ShapeCollection
from buildingmotif.dataclasses.validation import ValidationContext
from buildingmotif.namespaces import OWL, A
from buildingmotif.utils import (
    Triple,
    copy_graph,
    rewrite_shape_graph,
    shacl_inference,
    shacl_validate,
    skolemize_shapes,
)

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF


def _validate_uri(uri: str):
    parsed = rfc3987.parse(uri)
    if not parsed["scheme"]:
        raise ValueError(
            f"{uri} does not look like a valid URI, trying to serialize this will break."
        )


@dataclass
class Model:
    """This class mirrors :py:class:`database.tables.DBModel`."""

    _id: int
    _name: str
    _description: str
    graph: rdflib.Graph
    _bm: "BuildingMOTIF"
    _manifest_id: int

    @classmethod
    def create(cls, name: str, description: str = "") -> "Model":
        """Create a new model.

        :param name: new model name
        :type name: str
        :param description: new model description
        :type description: str
        :return: new model
        :rtype: Model
        """
        bm = get_building_motif()

        _validate_uri(name)
        db_model = bm.table_connection.create_db_model(name, description)

        g = rdflib.Graph()
        g.add((rdflib.URIRef(name), rdflib.RDF.type, rdflib.OWL.Ontology))
        graph = bm.graph_connection.create_graph(db_model.graph_id, g)

        return cls(
            _id=db_model.id,
            _name=db_model.name,
            _description=db_model.description,
            graph=graph,
            _bm=bm,
            _manifest_id=db_model.manifest_id,
        )

    @classmethod
    def load(cls, id: Optional[int] = None, name: Optional[str] = None) -> "Model":
        """Get model from database by id or name.

        :param id: model id, defaults to None
        :type id: Optional[int], optional
        :param name: model name, defaults to None
        :type name: Optional[str], optional
        :raises Exception: if neither id nor name provided
        :return: model
        :rtype: Model
        """
        bm = get_building_motif()
        if id is not None:
            db_model = bm.table_connection.get_db_model(id)
        elif name is not None:
            db_model = bm.table_connection.get_db_model_by_name(name)
        else:
            raise Exception("Neither id nor name provided to load Model")
        graph = bm.graph_connection.get_graph(db_model.graph_id)

        return cls(
            _id=db_model.id,
            _name=db_model.name,
            _description=db_model.description,
            graph=graph,
            _bm=bm,
            _manifest_id=db_model.manifest_id,
        )

    @property
    def id(self) -> Optional[int]:
        return self._id

    @id.setter
    def id(self, new_id):
        raise AttributeError("Cannot modify db id")

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name: str):
        self._bm.table_connection.update_db_model_name(self._id, new_name)
        self._name = new_name

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, new_description: str):
        self._bm.table_connection.update_db_model_description(self._id, new_description)
        self._description = new_description

    def add_triples(self, *triples: Triple) -> None:
        """Add the given triples to the model.

        :param triples: a sequence of triples to add to the graph
        :type triples: Triple
        """
        for triple in triples:
            self.graph.add(triple)

    def add_graph(self, graph: rdflib.Graph) -> None:
        """Add the given graph to the model.

        :param graph: the graph to add to the model
        :type graph: rdflib.Graph
        """
        self.graph += graph

    def validate(
        self,
        shape_collections: Optional[List[ShapeCollection]] = None,
        error_on_missing_imports: bool = True,
    ) -> "ValidationContext":
        """Validates this model against the given list of ShapeCollections.
        If no list is provided, the model will be validated against the model's "manifest".
        If a list of shape collections is provided, the manifest will *not* be automatically
        included in the set of shape collections.

        Loads all of the ShapeCollections into a single graph.

        :param shape_collections: a list of ShapeCollections against which the
            graph should be validated. If an empty list or None is provided, the
            model will be validated against the model's manifest.
        :type shape_collections: List[ShapeCollection]
        :param error_on_missing_imports: if True, raises an error if any of the dependency
            ontologies are missing (i.e. they need to be loaded into BuildingMOTIF), defaults
            to True
        :type error_on_missing_imports: bool, optional
        :return: An object containing useful properties/methods to deal with
            the validation results
        :rtype: ValidationContext
        """
        # TODO: determine the return types; At least a bool for valid/invalid,
        # but also want a report. Is this the base pySHACL report? Or a useful
        # transformation, like a list of deltas for potential fixes?
        shapeg = rdflib.Graph()
        if shape_collections is None or len(shape_collections) == 0:
            shape_collections = [self.get_manifest()]
        # aggregate shape graphs
        for sc in shape_collections:
            shapeg += sc.resolve_imports(
                error_on_missing_imports=error_on_missing_imports
            ).graph
        # inline sh:node for interpretability
        shapeg = rewrite_shape_graph(shapeg)

        # remove imports from sg
        shapeg.remove((None, OWL.imports, None))

        # skolemize the shape graph so we have consistent identifiers across
        # validation through the interpretation of the validation report
        shapeg = skolemize_shapes(shapeg)

        # TODO: do we want to preserve the materialized triples added to data_graph via reasoning?
        data_graph = copy_graph(self.graph)

        # validate the data graph
        valid, report_g, report_str = shacl_validate(
            data_graph, shapeg, engine=self._bm.shacl_engine
        )
        return ValidationContext(
            shape_collections,
            shapeg,
            valid,
            report_g,
            report_str,
            self,
        )

    def compile(self, shape_collections: List["ShapeCollection"]):
        """Compile the graph of a model against a set of ShapeCollections.

        :param shape_collections: list of ShapeCollections to compile the model
            against
        :type shape_collections: List[ShapeCollection]
        :return: copy of model's graph that has been compiled against the
            ShapeCollections
        :rtype: Graph
        """
        ontology_graph = rdflib.Graph()
        for shape_collection in shape_collections:
            ontology_graph += shape_collection.graph

        ontology_graph = skolemize_shapes(ontology_graph)

        model_graph = copy_graph(self.graph).skolemize()

        return shacl_inference(
            model_graph, ontology_graph, engine=self._bm.shacl_engine
        )

    def test_model_against_shapes(
        self,
        shape_collections: List["ShapeCollection"],
        shapes_to_test: List[rdflib.URIRef],
        target_class: rdflib.URIRef,
    ) -> Dict[rdflib.URIRef, "ValidationContext"]:
        """Validates the model against a list of shapes and generates a
        validation report for each.

        :param shape_collections: list of ShapeCollections needed to run shapes
        :type shape_collection: List[ShapeCollection]
        :param shapes_to_test: list of shape URIs to validate the model against
        :type shapes_to_test: List[URIRef]
        :param target_class: the class upon which to run the selected shapes
        :type target_class: URIRef
        :return: a dictionary that relates each shape to test URIRef to a
                 ValidationContext
        :rtype: Dict[URIRef, ValidationContext]
        """
        ontology_graph = rdflib.Graph()
        for shape_collection in shape_collections:
            ontology_graph += shape_collection.graph

        model_graph = copy_graph(self.graph)

        results = {}

        for shape_uri in shapes_to_test:
            targets = model_graph.query(
                f"""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?target
                WHERE {{
                    ?target rdf:type/rdfs:subClassOf* <{target_class}>

                }}
            """
            )
            temp_model_graph = copy_graph(model_graph)
            for (s,) in targets:
                temp_model_graph.add((URIRef(s), A, shape_uri))

            temp_model_graph += ontology_graph.cbd(shape_uri)

            # skolemize the shape graph so we have consistent identifiers across
            # validation through the interpretation of the validation report
            ontology_graph = ontology_graph.skolemize()

            valid, report_g, report_str = shacl_validate(
                temp_model_graph, ontology_graph
            )

            results[shape_uri] = ValidationContext(
                shape_collections,
                ontology_graph,
                valid,
                report_g,
                report_str,
                self,
            )

        return results

    def get_manifest(self) -> ShapeCollection:
        """Get ShapeCollection from model.

        :return: model's shape collection
        :rtype: ShapeCollection
        """
        return ShapeCollection.load(self._manifest_id)

    def update_manifest(self, manifest: ShapeCollection):
        """Updates the manifest for this model by adding in the contents
        of the shape graph inside the provided SHapeCollection

        :param manifest: the ShapeCollection containing additional shapes against which to validate this model
        :type manifest: ShapeCollection
        """
        self.get_manifest().graph += manifest.graph
