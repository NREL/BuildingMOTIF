import flask
from flask import Blueprint, current_app, jsonify, request
from flask_api import status
from rdflib import Graph, Namespace, URIRef
from rdflib.plugins.parsers.notation3 import BadSyntax
from sqlalchemy.orm.exc import NoResultFound

from buildingmotif.api.serializers.model import serialize
from buildingmotif.dataclasses import Library, Model, ShapeCollection
from buildingmotif.ingresses import BACnetNetwork, BACnetToBrickIngress

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

    g = Graph() + model.graph

    return g.serialize(format="ttl"), status.HTTP_200_OK


@blueprint.route("/<models_id>/target_nodes", methods=(["GET"]))
def get_target_nodes(models_id: int) -> Graph:
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

    result = model.graph.query(
        """
        SELECT ?type WHERE {
        ?target rdf:type ?type
        }
    """
    )
    result = list({r for r in result})
    result.sort()

    return result, status.HTTP_200_OK


@blueprint.route("/<models_id>/point_names", methods=(["GET"]))
def get_point_names(models_id: int) -> Graph:
    """Get model's point names.

    :param models_id: model id
    :type models_id: int
    :return: requested model graph
    :rtype: rdflib.Graph
    """
    try:
        m = Model.load(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    full_graph = m.with_imports()
    response = full_graph.query(
        """
    PREFIX ref: <https://brickschema.org/schema/ref#>
    PREFIX bacnet: <http://data.ashrae.org/bacnet/2020#>
    SELECT ?point ?label WHERE {
        ?point rdf:type/rdfs:subClassOf* brick:Point .
        { ?point rdfs:label ?label }
        UNION
        { ?point ref:hasExternalReference/bacnet:object-identifier ?label }
    }
    """
    )

    result: list[str] = [str(row["label"]) for row in response]

    return result, status.HTTP_200_OK


@blueprint.route("", methods=(["POST"]))
def create_model() -> flask.Response:
    """Create model

    :return: new model
    :rtype: Model
    """
    if request.content_type and not request.content_type.startswith(
        "multipart/form-data"
    ):
        return {
            "message": "request content type must be form_data"
        }, status.HTTP_400_BAD_REQUEST

    name = request.form.get("name")
    description = request.form.get("description", "")

    if name is None:
        return {"message": "must give name"}, status.HTTP_400_BAD_REQUEST

    try:
        model = Model.create(name, description)
    except ValueError:
        return {
            "message": f"{name} does not look like a valid URI, "
            "trying to serialize this will break."
        }, status.HTTP_400_BAD_REQUEST

    files = request.files.getlist("files[]")
    file = None if len(files) == 0 else files[0]

    if file:
        bacnet = BACnetNetwork.loads(file.read())
        tobrick = BACnetToBrickIngress(current_app.building_motif, bacnet)
        BLDG = Namespace("urn:building/")
        model.add_graph(tobrick.graph(BLDG))

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


@blueprint.route("/<models_id>/validate", methods=(["POST"]))
def validate_model(models_id: int) -> flask.Response:
    # get model
    try:
        model = Model.load(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    shape_collections = []

    # no body provided -- default to model manifest and default SHACL engine
    if request.content_length is None:
        shape_collections = [model.get_manifest()]
    else:
        # get body
        if request.content_type != "application/json":
            return flask.Response(
                {"message": "request content type must be json"},
                status.HTTP_400_BAD_REQUEST,
            )
        try:
            body = request.json
        except Exception as e:
            return {"message": f"cannot read body {e}"}, status.HTTP_400_BAD_REQUEST

        if body is not None and not isinstance(body, dict):
            return {"message": "body is not dict"}, status.HTTP_400_BAD_REQUEST
        shape_collections = []
        body = body if body is not None else {}
        nonexistent_libraries = []
        for library_id in body.get("library_ids", []):
            try:
                shape_collection = Library.load(library_id).get_shape_collection()
                shape_collections.append(shape_collection)
            except NoResultFound:
                nonexistent_libraries.append(library_id)
        if len(nonexistent_libraries) > 0:
            return {
                "message": f"Libraries with ids {nonexistent_libraries} do not exist"
            }, status.HTTP_400_BAD_REQUEST

    # if shape_collections is empty, model.validate will default
    # to the model's manifest
    vaildation_context = model.validate(shape_collections)

    return {
        "message": vaildation_context.report_string,
        "valid": vaildation_context.valid,
        "reasons": {
            focus_node: list(set(gd.reason() for gd in grahdiffs))
            for focus_node, grahdiffs in vaildation_context.diffset.items()
        },
    }, status.HTTP_200_OK


@blueprint.route("/<models_id>/validate_shape", methods=(["POST"]))
def validate_shape(models_id: int) -> flask.Response:
    # get model
    try:
        model = Model.load(models_id)
    except NoResultFound:
        return {"message": f"No model with id {models_id}"}, status.HTTP_404_NOT_FOUND

    # get body
    if request.content_type != "application/json":
        return flask.Response(
            {"message": "request content type must be json"},
            status.HTTP_400_BAD_REQUEST,
        )
    try:
        body = request.json
    except Exception as e:
        return {"message": f"cannot read body {e}"}, status.HTTP_400_BAD_REQUEST

    if not isinstance(body, dict):
        return {"message": "body is not dict"}, status.HTTP_400_BAD_REQUEST

    # shape collections
    shape_collections = []
    nonexistent_shape_collections = []
    for shape_collection_id in body.get("shape_collection_ids", []):
        try:
            shape_collection = ShapeCollection.load(shape_collection_id)
            shape_collections.append(shape_collection)
        except NoResultFound:
            nonexistent_shape_collections.append(shape_collection_id)
    if len(nonexistent_shape_collections) > 0:
        return {
            "message": f"shape collections with ids {nonexistent_shape_collections} do not exist"
        }, status.HTTP_400_BAD_REQUEST

    if body.get("target_class", None) is None:
        return {
            "message": "target class is required to execute this endpoint"
        }, status.HTTP_400_BAD_REQUEST

    shape_uris = [URIRef(shape_uri) for shape_uri in body.get("shape_uris", [])]
    target_class = URIRef(body.get("target_class"))

    # test
    conformance = model.test_model_against_shapes(
        shape_collections=shape_collections,
        shapes_to_test=shape_uris,
        target_class=target_class,
    )

    result = {}
    for shape_uri, validation_context in conformance.items():
        diffsets = validation_context.diffset.values()
        reasons = [diff.reason() for diffset in diffsets for diff in diffset]
        result[shape_uri] = reasons

    return result, status.HTTP_200_OK
