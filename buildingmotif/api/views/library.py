import flask
from flask import Blueprint, current_app, jsonify
from flask_api import status
from sqlalchemy.orm.exc import NoResultFound

from buildingmotif.api.serializers.library import serialize

blueprint = Blueprint("libraries", __name__)


@blueprint.route("", methods=(["GET"]))
def get_all_libraries() -> flask.Response:
    """Get all libraries.

    :return: all libraries
    :rtype: List[Libraries]
    """
    db_libs = current_app.building_motif.table_connection.get_all_db_libraries()

    return jsonify(serialize(db_libs)), status.HTTP_200_OK


@blueprint.route("/<library_id>", methods=(["GET"]))
def get_library(library_id: int) -> flask.Response:
    """Get library by id.

    :param library_id: library id
    :type library_id: int
    :return: requested library
    :rtype: flask.Response
    """
    try:
        db_lib = current_app.building_motif.table_connection.get_db_library_by_id(
            library_id
        )
    except NoResultFound:
        return {
            "message": f"No library with id {library_id}"
        }, status.HTTP_404_NOT_FOUND

    return jsonify(serialize(db_lib)), status.HTTP_200_OK
