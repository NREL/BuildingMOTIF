from typing import Dict, List, Tuple

import flask
import pyshacl
from flask import Blueprint, current_app, jsonify, request
from flask_api import status
from rdflib import Graph
from rdflib.plugins.parsers.notation3 import BadSyntax
from sqlalchemy.orm.exc import NoResultFound

from buildingmotif.api.serializers.model import serialize
from buildingmotif.dataclasses import Library, Model, ShapeCollection
from buildingmotif.dataclasses.validation import ValidationContext

blueprint = Blueprint("models", __name__)


@blueprint.route("", methods=(["GET"]))
def get_all_models() -> flask.Response:
    """Get all models.

    :return: all models
    :rtype: flask.Response
    """
    db_models = current_app.building_motif.table_connection.get_all_db_models()

    return jsonify(serialize(db_models))


@blueprint.route("/<models_id>", methods=(["GET"]))
def get_model(models_id: int) -> flask.Response:
    """Get Model by id.

    :param models_id: model id
    :type models_id: int
    :return: requested model
    :rtype: flask.Response
    """
    try:
        model = current_app.building_motif.table_connection.get_db_model(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    return jsonify(serialize(model)), status.HTTP_200_OK


@blueprint.route("/<models_id>/graph", methods=(["GET"]))
def get_model_graph(models_id: int) -> Graph:
    """Get model graph by id.

    :param models_id: model id
    :type models_id: int
    :return: requested model graph
    :rtype: rdflib.Graph
    """
    try:
        model = Model.load(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    return model.graph.serialize(format="ttl"), status.HTTP_200_OK


@blueprint.route("", methods=(["POST"]))
def create_model() -> flask.Response:
    """Create model

    :return: new model
    :rtype: Model
    """
    if request.content_type != "application/json":
        return {
            "message": "request content type must be json"
        }, status.HTTP_400_BAD_REQUEST

    name = request.json.get("name")
    description = request.json.get("description")

    if name is None:
        return {"message": "must give name"}, status.HTTP_400_BAD_REQUEST

    try:
        model = Model.create(name, description)
    except ValueError:
        return {
            "message": f"{name} does not look like a valid URI, "
            "trying to serialize this will break."
        }, status.HTTP_400_BAD_REQUEST

    current_app.building_motif.session.commit()

    model = current_app.building_motif.table_connection.get_db_model(model.id)

    return jsonify(serialize(model)), status.HTTP_201_CREATED


@blueprint.route("/<models_id>/graph", methods=(["PATCH", "PUT"]))
def update_model_graph(models_id: int) -> flask.Response:
    """Update model graph.

    Takes xml body of ttl formated graph.

    :param models_id: model id
    :type models_id: int
    :return: updated model graph
    :rtype: rdflib.Graph
    """
    try:
        model = Model.load(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    if request.content_type != "application/xml":
        return {
            "message": "request content type must be xml"
        }, status.HTTP_400_BAD_REQUEST

    try:
        graph = Graph().parse(data=request.data, format="ttl")
    except BadSyntax as e:
        return {"message": f"data is unreadable: {e}"}, status.HTTP_400_BAD_REQUEST

    if request.method == "PUT":
        model.graph.remove((None, None, None))

    model.add_graph(graph)

    current_app.building_motif.session.commit()

    return model.graph.serialize(format="ttl")


def _get_shape_collections_and_ontology_and_schal_graph(
    body: Dict,
) -> Tuple[List[ShapeCollection], Graph, Graph]:
    # get shape collections
    shape_collections = []
    for body_item in body:
        try:
            library_id = body_item["library_id"]
            shape_collection = Library.load(library_id).get_shape_collection()
            shape_collections.append(shape_collection)
        except KeyError as e:
            raise KeyError(
                f"body item {body_item} doees not contain a 'library_id'"
            ) from e
        except NoResultFound as e:
            raise NoResultFound(f"No library with id {library_id}") from e

    # buiild ontology graph
    ontology_graph = Graph()
    for shape_collection in shape_collections:
        ontology_graph += shape_collection.graph

    # build shacl graph
    shacl_graph = Graph()
    for body_item in body:
        try:
            shape_uri = body_item["shape_uri"]
            shacl_graph += ontology_graph.cbd(shape_uri)
        except KeyError as e:
            raise KeyError(
                f"body item {body_item} doees not contain a 'shape_uri'"
            ) from e

    return shape_collections, ontology_graph, shacl_graph


@blueprint.route("/<models_id>/validate", methods=(["POST"]))
def validate_model(models_id: int) -> flask.Response:
    # get model
    try:
        model = Model.load(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    # get body
    if request.content_type != "application/json":
        return {
            "message": "request content type must be json"
        }, status.HTTP_400_BAD_REQUEST
    try:
        body = request.json
    except Exception:
        return {"message": "cannot read body"}, status.HTTP_400_BAD_REQUEST

    try:
        (
            shape_collections,
            ontology_graph,
            shacl_graph,
        ) = _get_shape_collections_and_ontology_and_schal_graph(body)
    except (KeyError, NoResultFound) as e:
        return {"message": str(e)}, status.HTTP_400_BAD_REQUEST

    # validate
    valid, report_g, report_str = pyshacl.validate(
        data_graph=model.graph,
        shacl_graph=shacl_graph,
        ont_graph=ontology_graph,
        allow_warnings=True,
        advanced=True,
        js=True,
    )
    vaildation_context = ValidationContext(
        shape_collections,
        valid,
        report_g,
        report_str,
        model,
    )

    return {
        "message": vaildation_context.report_string,
        "valid": vaildation_context.valid,
        "reasons": [x.reason() for x in vaildation_context.diffset],
    }
