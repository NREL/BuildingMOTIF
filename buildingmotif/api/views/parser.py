import logging
from typing import Type

import flask
from flask import Blueprint, jsonify, request
from flask_api import status

from buildingmotif.label_parsing.combinators import (
    Parser,
    abbreviations,
    as_identifier,
    choice,
    constant,
    extend_if_match,
    identifier,
    many,
    maybe,
    regex,
    rest,
    sequence,
    string,
    until,
)
from buildingmotif.label_parsing.parser import parse

log = logging.getLogger()

blueprint = Blueprint("parsers", __name__)

parsers_by_name: dict[str, Type[Parser]] = {
    "abbreviations": abbreviations,
    "sequence": sequence,
    "string": string,
    "constant": constant,
    "regex": regex,
    "many": many,
    "maybe": maybe,
    "rest": rest,
    "choice": choice,
    "until": until,
    "extend_if_match": extend_if_match,
    "as_identifier": as_identifier,
    "identifier": identifier,
}


@blueprint.route("", methods=(["POST"]))
def evaluate() -> flask.Response:
    raw_data = request.json

    parser_dict = raw_data.get("parsers")
    name, args = parser_dict.get("name"), parser_dict.get("args")
    my_parser = parsers_by_name[name](**args)
    point_labels = raw_data.get("point_labels")

    return (
        jsonify([parse(my_parser, point_label) for point_label in point_labels]),
        status.HTTP_200_OK,
    )
