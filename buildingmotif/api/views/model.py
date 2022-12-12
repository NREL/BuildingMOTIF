import flask
from flask import Blueprint, current_app, jsonify, request
from flask_api import status
from rdflib import Graph
from rdflib.plugins.parsers.notation3 import BadSyntax
from sqlalchemy.orm.exc import NoResultFound

from buildingmotif.api.serializers.model import serialize
from buildingmotif.dataclasses import Library, Model

blueprint = Blueprint("models", __name__)


@blueprint.route("", methods=(["GET"]))
def get_all_models() -> flask.Response:
    """Get all models.

    :return: All models.
    :rtype: List[Model]
    """
    db_models = current_app.building_motif.table_connection.get_all_db_models()

    return jsonify(serialize(db_models))


@blueprint.route("/<models_id>", methods=(["GET"]))
def get_model(models_id: int) -> flask.Response:
    """get model with id

    :param models_id: model id
    :type models_id: int
    :return: requested id
    :rtype: Model
    """
    try:
        model = current_app.building_motif.table_connection.get_db_model(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    return jsonify(serialize(model)), status.HTTP_200_OK


@blueprint.route("/<models_id>/graph", methods=(["GET"]))
def get_model_graph(models_id: int) -> flask.Response:
    """get model with id

    :param models_id: model id
    :type models_id: int
    :return: requested id
    :rtype: Model
    """
    try:
        model = Model.load(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    return model.graph.serialize(format="ttl"), status.HTTP_200_OK


@blueprint.route("/<models_id>/graph", methods=(["PATCH"]))
def update_model_graph(models_id: int) -> flask.Response:
    """update model graph

    Takes xml body of ttl formated graph.

    :param models_id: model id
    :type models_id: int
    :return: Updated model
    :rtype: Model
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

    model.graph.remove((None, None, None))
    model.add_graph(graph)

    current_app.building_motif.session.commit()

    return model.graph.serialize(format="ttl")


@blueprint.route("/<models_id>/validate", methods=(["GET"]))
def validate_model(models_id: int) -> flask.Response:
    try:
        model = Model.load(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    if request.content_type != "application/json":
        return {
            "message": "request content type must be json"
        }, status.HTTP_400_BAD_REQUEST

    library_id = request.get_json().get("library_id")

    if library_id is None:
        return {"message": "body must contain library_id"}, status.HTTP_400_BAD_REQUEST

    try:
        library = Library.load(library_id)
    except NoResultFound:
        return {
            "message": f"No library with id {library_id}"
        }, status.HTTP_404_NOT_FOUND

    vaildation_context = model.validate([library.get_shape_collection()])

    return jsonify(
        {"valid": vaildation_context.valid, "message": vaildation_context.report_string}
    )
