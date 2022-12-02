from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional

import pyshacl
import rdflib

from buildingmotif import get_building_motif
from buildingmotif.dataclasses.shape_collection import ShapeCollection
from buildingmotif.dataclasses.validation import ValidationContext
from buildingmotif.namespaces import A
from buildingmotif.utils import Triple, copy_graph

if TYPE_CHECKING:
    from buildingmotif import BuildingMOTIF


@dataclass
class Model:
    """This class mirrors :py:class:`database.tables.DBModel`."""

    _id: int
    _name: str
    _description: str
    graph: rdflib.Graph
    _bm: "BuildingMOTIF"

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
        )

    @classmethod
    def load(cls, id: Optional[int] = None, name: Optional[str] = None) -> "Model":
        """Get model from database by id or name.

        :param id: model id
        :type id: int
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

    def validate(self, shape_collections: List[ShapeCollection]) -> "ValidationContext":
        """Validates this model against the given ShapeCollections.

        Loads all of the ShapeCollections into a single graph.

        :param shape_collections: a list of ShapeCollections against which the
            graph should be validated
        :type shape_collections: List[ShapeCollection]
        :return: An object containing useful properties/methods to deal with
            the validation results
        :rtype: ValidationContext
        """
        # TODO: determine the return types; At least a bool for valid/invalid,
        # but also want a report. Is this the base pySHACL report? Or a useful
        # transformation, like a list of deltas for potential fixes?
        shapeg = rdflib.Graph()
        for sc in shape_collections:
            # inline sh:node for interpretability
            shapeg += sc._inline_sh_node()
        # TODO: do we want to preserve the materialized triples added to data_graph via reasoning?
        data_graph = copy_graph(self.graph)
        valid, report_g, report_str = pyshacl.validate(
            data_graph,
            shacl_graph=shapeg,
            ont_graph=shapeg,
            advanced=True,
            js=True,
            allow_warnings=True,
            # inplace=True,
        )
        assert isinstance(report_g, rdflib.Graph)
        return ValidationContext(
            shape_collections,
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

        ontology_graph = ontology_graph.skolemize()

        model_graph = copy_graph(self.graph).skolemize()

        # We use a fixed-point computation approach to 'compiling' RDF models.
        # We accomlish this by keeping track of the size of the graph before and after
        # the inference step. If the size of the graph changes, then we know that the
        # inference has had some effect. We do this at most 3 times to avoid looping
        # forever.
        pre_compile_length = len(model_graph)  # type: ignore
        pyshacl.validate(
            data_graph=model_graph,
            shacl_graph=ontology_graph,
            ont_graph=ontology_graph,
            advanced=True,
            inplace=True,
            js=True,
        )
        post_compile_length = len(model_graph)  # type: ignore

        attempts = 3
        while attempts > 0 and post_compile_length != pre_compile_length:
            pre_compile_length = len(model_graph)  # type: ignore
            pyshacl.validate(
                data_graph=model_graph,
                shacl_graph=ontology_graph,
                ont_graph=ontology_graph,
                advanced=True,
                inplace=True,
                js=True,
            )
            post_compile_length = len(model_graph)  # type: ignore
            attempts -= 1
        model_graph -= ontology_graph
        return model_graph.de_skolemize()

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
            targets = model_graph.triples((None, A, target_class))
            temp_model_graph = copy_graph(model_graph)
            for s, _, _ in targets:
                temp_model_graph.add((s, A, shape_uri))

            temp_model_graph += ontology_graph.cbd(shape_uri)

            valid, report_g, report_str = pyshacl.validate(
                data_graph=temp_model_graph,
                ont_graph=ontology_graph,
                allow_warnings=True,
                advanced=True,
                js=True,
            )
            results[shape_uri] = ValidationContext(
                shape_collections,
                valid,
                report_g,
                report_str,
                self,
            )

        return results
