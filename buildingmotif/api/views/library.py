import flask
from flask import Blueprint, current_app, jsonify

from buildingmotif.api.serializers.library import serialize

blueprint = Blueprint("libraries", __name__)


@blueprint.route("", methods=(["GET"]))
def get_all_libraries() -> flask.Response:
    """get all libraries

    :return: all libraries
    :rtype: List[Libraries]
    """
    db_libs = current_app.building_motif.table_connection.get_all_db_libraries()

    return jsonify(serialize(db_libs))


@blueprint.route("/<library_id>", methods=(["GET"]))
def get_library(library_id: int) -> flask.Response:
    """get library by id

    :param library_id: library id
    :type library_id: int
    :return: requested library
    :rtype: flask.Response
    """
    db_lib = current_app.building_motif.table_connection.get_db_library_by_id(
        library_id
    )

    return jsonify(serialize(db_lib))
