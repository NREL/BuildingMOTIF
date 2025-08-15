from typing import Dict, List
from urllib.parse import unquote

import flask
from flask import Blueprint, current_app, jsonify
from flask_api import status
from rdflib import URIRef

from buildingmotif.api.serializers.library import serialize
from buildingmotif.database.errors import LibraryNotFound
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
    definition_types = [
        URIRef("https://nrel.gov/BuildingMOTIF#Sequence_Of_Operations"),
        URIRef("https://nrel.gov/BuildingMOTIF#Analytics_Application"),
        URIRef("https://nrel.gov/BuildingMOTIF#System_Specification"),
    ]
    results: Dict[URIRef, List[Dict]] = {dt: [] for dt in definition_types}

    db_libs = current_app.building_motif.table_connection.get_all_db_libraries()
    for db_lib in db_libs:
        shape_collection = ShapeCollection.load(db_lib.shape_collection.id)
        for dt in definition_types:
            results[dt] += [
                {
                    "shape_uri": str(shape),
                    "label": label,
                    "library_name": db_lib.name,
                    "shape_collection_id": shape_collection.id,
                }
                for (shape, label) in shape_collection.get_shapes_of_definition_type(
                    dt, include_labels=True
                )
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
    except LibraryNotFound:
        return {"message": f"ID: {library_id}"}, status.HTTP_404_NOT_FOUND

    return jsonify(serialize(db_lib)), status.HTTP_200_OK


@blueprint.route("/<library_id>/classes", methods=(["GET"]))
def get_library_classes(library_id: int) -> flask.Response:
    """Get all classes from a library's shape collection.

    An optional 'subclasses_of' query parameter can be provided to get all
    subclasses of a given class.

    :param library_id: library id
    :type library_id: int
    :return: all classes in shape collection
    :rtype: flask.Response
    """
    try:
        db_lib = current_app.building_motif.table_connection.get_db_library(library_id)
    except LibraryNotFound:
        current_app.logger.error(f"Library with ID {library_id} not found.")
        return {"message": f"ID: {library_id}"}, status.HTTP_404_NOT_FOUND

    shape_collection = ShapeCollection.load(db_lib.shape_collection.id)

    subclass_of_uri = flask.request.args.get("subclasses_of")
    if subclass_of_uri:
        subclass_of_uri = unquote(subclass_of_uri)
    current_app.logger.info(
        f"Fetching classes from library {library_id} with subclass_of_uri: {subclass_of_uri}"
    )

    try:
        if subclass_of_uri:
            query = f"""
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                SELECT ?cls ?label ?definition
                WHERE {{
                    ?cls rdfs:subClassOf+ <{subclass_of_uri}> .
                    FILTER(!isBlank(?cls))
                    OPTIONAL {{ ?cls rdfs:label ?label . }}
                    OPTIONAL {{ ?cls skos:definition ?definition . }}
                }}
            """
        else:
            query = """
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                SELECT ?cls ?label ?definition
                WHERE {
                    { ?cls a rdfs:Class . }
                    UNION
                    { ?cls a owl:Class . }
                    FILTER(!isBlank(?cls))
                    OPTIONAL { ?cls rdfs:label ?label . }
                    OPTIONAL { ?cls skos:definition ?definition . }
                }
            """
        current_app.logger.info(f"Executing query: {query}")
        query_results = shape_collection.graph.query(query)

        results = [
            {
                "uri": str(res.cls),
                "label": str(res.label) if res.label else None,
                "definition": str(res.definition) if res.definition else None,
            }
            for res in query_results
        ]

        return jsonify(results), status.HTTP_200_OK
    except Exception:
        current_app.logger.error("Error processing get_library_classes", exc_info=True)
        return (
            {"message": "Internal Server Error"},
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@blueprint.route("/<library_id>/shape_collection/ontology_name", methods=(["GET"]))
def get_library_shape_collection_ontology_name(library_id: int) -> flask.Response:
    """Get the ontology name (graph identifier) of the library's shape collection.

    :param library_id: library id
    :type library_id: int
    :return: {"ontology_name": string | null}
    :rtype: flask.Response
    """
    try:
        db_lib = current_app.building_motif.table_connection.get_db_library(library_id)
    except LibraryNotFound:
        current_app.logger.error(f"Library with ID {library_id} not found.")
        return {"message": f"ID: {library_id}"}, status.HTTP_404_NOT_FOUND

    ident = db_lib.shape_collection.graph_id
    return jsonify({"ontology_name": ident}), status.HTTP_200_OK


@blueprint.route("/<library_id>/shape_collection/shapes", methods=(["GET"]))
def get_library_shape_collection_shapes(library_id: int) -> flask.Response:
    """List all SHACL NodeShapes defined in a library's shape collection.

    :param library_id: library id
    :type library_id: int
    :return: array of {shape_uri, label}
    :rtype: flask.Response
    """
    try:
        db_lib = current_app.building_motif.table_connection.get_db_library(library_id)
    except LibraryNotFound:
        current_app.logger.error(f"Library with ID {library_id} not found.")
        return {"message": f"ID: {library_id}"}, status.HTTP_404_NOT_FOUND

    shape_collection = ShapeCollection.load(db_lib.shape_collection.id)

    query = """
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?shape ?label
        WHERE {
            ?shape a sh:NodeShape .
            OPTIONAL { ?shape rdfs:label ?label . }
        }
    """
    rows = shape_collection.graph.query(query)
    results = [
        {"shape_uri": str(r.shape), "label": str(r.label) if r.label else None}
        for r in rows
    ]

    # sort for deterministic output
    results.sort(key=lambda x: x["shape_uri"])
    return jsonify(results), status.HTTP_200_OK
