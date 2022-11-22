import flask
from flask import Blueprint, current_app, jsonify, request
from flask_api import status
from rdflib import Graph
from rdflib.plugins.parsers.notation3 import BadSyntax
from sqlalchemy.orm.exc import NoResultFound

from buildingmotif.api.serializers.model import serialize
from buildingmotif.dataclasses import Model

blueprint = Blueprint("models", __name__)


@blueprint.route("", methods=(["GET"]))
def get_all_models() -> flask.Response:
    """Get all Models.

    :return: All models.
    :rtype: flask.Response
    """
    db_models = current_app.building_motif.table_connection.get_all_db_models()

    return jsonify(serialize(db_models))


@blueprint.route("/<models_id>", methods=(["GET"]))
def get_model(models_id: int) -> flask.Response:
    """Get Model by id.

    :param models_id: The Model id.
    :type models_id: int
    :return: The requested Model.
    :rtype: flask.Response
    """
    try:
        model = current_app.building_motif.table_connection.get_db_model(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    return jsonify(serialize(model)), status.HTTP_200_OK


@blueprint.route("/<models_id>/graph", methods=(["GET"]))
def get_model_graph(models_id: int) -> Graph:
    """Get Model Graph by id.

    :param models_id: The Model id.
    :type models_id: int
    :return: The requested Model Graph.
    :rtype: rdflib.Graph
    """
    try:
        model = Model.load(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    return model.graph.serialize(format="ttl"), status.HTTP_200_OK


@blueprint.route("/<models_id>/graph", methods=(["PATCH"]))
def update_model_graph(models_id: int) -> Graph:
    """Update Model graph.

    Takes xml body of ttl formated graph.

    :param models_id: The Model id.
    :type models_id: int
    :return: The requested updated Model Graph.
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

    model.graph.remove((None, None, None))
    model.add_graph(graph)

    current_app.building_motif.session.commit()

    return model.graph.serialize(format="ttl")
