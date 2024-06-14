import logging

import flask
from flask import Blueprint, jsonify, request
from flask_api import status

from buildingmotif.api.serializers.parser import deserialize
from buildingmotif.label_parsing.parser import parse

log = logging.getLogger()

blueprint = Blueprint("parsers", __name__)


@blueprint.route("", methods=(["POST"]))
def evaluate() -> flask.Response:
    raw_data = request.json

    my_parser = deserialize(raw_data.get("parsers"))
    point_labels = raw_data.get("point_labels")

    return (
        jsonify([parse(my_parser, point_label) for point_label in point_labels]),
        status.HTTP_200_OK,
    )
