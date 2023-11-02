import flask
from flask import Blueprint, current_app, jsonify
from flask_api import status
from sqlalchemy.orm.exc import NoResultFound

from buildingmotif.api.serializers.library import serialize
from buildingmotif.dataclasses.shape_collection import ShapeCollection

blueprint = Blueprint("libraries", __name__)

get_shape_query = """
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    SELECT ?shape ?label ?desc
    WHERE {
        ?shape a sh:NodeShape ;
            sh:targetClass|sh:targetSubjectOf|sh:targetObjectsOf|sh:targetNode ?target .
        OPTIONAL { ?shape rdfs:label ?label }
        OPTIONAL { ?shape skos:description ?desc }
    }
"""


@blueprint.route("", methods=(["GET"]))
def get_all_libraries() -> flask.Response:
    """Get all libraries.

    :return: all libraries
    :rtype: flask.Response
    """
    db_libs = current_app.building_motif.table_connection.get_all_db_libraries()

    return jsonify(serialize(db_libs)), status.HTTP_200_OK


@blueprint.route("/shapes", methods=(["GET"]))
def get_all_shapes() -> flask.Response:
    """Get all shapes.

    :return: all shapes
    :rtype: flask.Response
    """
    results = []

    db_libs = current_app.building_motif.table_connection.get_all_db_libraries()
    for db_lib in db_libs:
        shape_collection = ShapeCollection.load(db_lib.shape_collection.id)
        shapes = shape_collection.graph.query(get_shape_query)
        results += [
            {
                "library_name": db_lib.name,
                "library_id": db_lib.id,
                "label": label,
                "uri": uri,
                "description": description,
            }
            for uri, label, description in shapes
        ]

    return jsonify(results), status.HTTP_200_OK


@blueprint.route("/<library_id>", methods=(["GET"]))
def get_library(library_id: int) -> flask.Response:
    """Get library by id.

    :param library_id: library id
    :type library_id: int
    :return: requested library
    :rtype: flask.Response
    """
    try:
        db_lib = current_app.building_motif.table_connection.get_db_library(library_id)
    except NoResultFound:
        return {
            "message": f"No library with id {library_id}"
        }, status.HTTP_404_NOT_FOUND

    return jsonify(serialize(db_lib)), status.HTTP_200_OK
