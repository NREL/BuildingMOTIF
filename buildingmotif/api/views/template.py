from typing import Dict

import flask
from flask import Blueprint, current_app, jsonify, request
from flask_api import status
from rdflib import Literal, URIRef
from rdflib.term import Node
from sqlalchemy.orm.exc import NoResultFound

from buildingmotif.api.serializers.template import serialize
from buildingmotif.dataclasses import Template

blueprint = Blueprint("templates", __name__)


@blueprint.route("", methods=(["GET"]))
def get_all_templates() -> flask.Response:
    """Get all templates.

    :return: all templates
    :rtype: List[Template]
    """
    db_templates = current_app.building_motif.table_connection.get_all_db_templates()

    return jsonify(serialize(db_templates)), status.HTTP_200_OK


@blueprint.route("/<templates_id>", methods=(["GET"]))
def get_template(templates_id: int) -> flask.Response:
    """Get Template with id.

    :param templates_id: template id
    :type templates_id: int
    :return: requested id
    :rtype: Template
    """
    include_parameters = request.args.get("parameters", False)

    try:
        template = current_app.building_motif.table_connection.get_db_template_by_id(
            templates_id
        )
    except NoResultFound:
        return {
            "message": f"No template with id {templates_id}"
        }, status.HTTP_404_NOT_FOUND

    return jsonify(serialize(template, include_parameters)), status.HTTP_200_OK


@blueprint.route("/<template_id>/evaluate", methods=(["POST"]))
def evaluate(template_id: int) -> flask.Response:
    try:
        template = Template.load(template_id)
    except NoResultFound:
        return {
            "message": f"No template with id {template_id}"
        }, status.HTTP_404_NOT_FOUND

    if request.content_type != "application/json":
        return {
            "message": "request content type must be json"
        }, status.HTTP_400_BAD_REQUEST

    # parse bindings from input JSON
    bindings = get_bindings(request.get_json())
    graph_or_template = template.evaluate(bindings=bindings)
    if isinstance(graph_or_template, Template):
        graph = graph_or_template.body
    else:
        graph = graph_or_template

    return graph.serialize(format="ttl"), status.HTTP_200_OK


def get_bindings(binding_dict) -> Dict[str, Node]:
    bindings = {}
    for param, definition in binding_dict.items():
        if "@id" in definition:
            bindings[param] = URIRef(definition["@id"])
        if "@literal" in definition:
            dtype = definition.get("@datatype")
            bindings[param] = Literal(
                definition["@literal"], datatype=URIRef(dtype) if dtype else None
            )
    return bindings
