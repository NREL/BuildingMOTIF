import logging

import flask
from flask import Blueprint, current_app, jsonify, request
from flask_api import status
from rdflib import Graph, URIRef
from rdflib.plugins.parsers.notation3 import BadSyntax

from buildingmotif.api.serializers.model import serialize
from buildingmotif.database.errors import (
    LibraryNotFound,
    ModelNotFound,
    ShapeCollectionNotFound,
)
from buildingmotif.dataclasses import Library, Model, ShapeCollection
from buildingmotif.exports.brick2af.validation import generate_report
from buildingmotif.namespaces import OWL, RDF, PARAM, bind_prefixes

blueprint = Blueprint("models", __name__)
logger = logging.getLogger()


def _parse_bool_param(name: str, default: bool = False) -> bool:
    val = request.args.get(name)
    if val is None:
        return default
    return str(val).lower() in ("1", "true", "yes", "y", "on")


def _parse_iteration_params():
    min_iterations_arg = request.args.get("min_iterations")
    max_iterations_arg = request.args.get("max_iterations")
    min_iterations = 1
    max_iterations = 3
    try:
        if min_iterations_arg is not None:
            min_iterations = int(min_iterations_arg)
        if max_iterations_arg is not None:
            max_iterations = int(max_iterations_arg)
    except ValueError:
        raise ValueError("min_iterations and max_iterations must be integers")
    if min_iterations < 1 or max_iterations < 1:
        raise ValueError("min_iterations and max_iterations must be >= 1")
    return min_iterations, max_iterations


def _select_shape_collections(model):
    # Determine which shape collections to use for validation
    if request.content_length is None:
        return [model.get_manifest()], []
    if request.content_type != "application/json":
        raise ValueError("request content type must be json")
    try:
        body = request.json
    except Exception as e:
        raise ValueError(f"cannot read body {e}")

    if body is not None and not isinstance(body, dict):
        raise ValueError("body is not dict")

    body = body if body is not None else {}
    nonexistent_libraries = []
    shape_collections = []
    for library_id in body.get("library_ids", []):
        if library_id == 0:  # 0 is 'model manifest'
            shape_collections.append(model.get_manifest())
            continue
        try:
            shape_collection = Library.load(library_id).get_shape_collection()
            shape_collections.append(shape_collection)
        except LibraryNotFound:
            nonexistent_libraries.append(library_id)

    if len(shape_collections) == 0:
        shape_collections = [model.get_manifest()]

    return shape_collections, nonexistent_libraries


def _compute_validation_context(model, shape_collections, min_iterations, max_iterations):
    compiled = model.compile(
        shape_collections,
        min_iterations=min_iterations,
        max_iterations=max_iterations,
    )
    ctx = compiled.validate(
        error_on_missing_imports=False,
        min_iterations=min_iterations,
        max_iterations=max_iterations,
    )
    return ctx


def _templates_payload_from_context(ctx):
    # Generate templates from diffs and serialize bodies + parameter metadata
    payload = []
    for focus, templ in ctx.as_templates_with_focus():
        inlined = templ.inline_dependencies()
        body_graph = inlined.body
        bind_prefixes(body_graph)
        ttl_body = body_graph.serialize(format="ttl")

        params_attr = getattr(inlined, "parameters", None)
        if isinstance(params_attr, dict):
            param_names = list(params_attr.keys())
        elif isinstance(params_attr, (list, tuple, set)):
            param_names = list(params_attr)
        else:
            param_names = []

        parameters = []
        for pname in param_names:
            pnode = PARAM[pname]
            types = sorted({str(o) for o in body_graph.objects(pnode, RDF.type)})
            parameters.append({"name": pname, "types": types})

        payload.append({
            "body": ttl_body,
            "parameters": parameters,
            "focus": (str(focus) if focus is not None else None),
        })

    return payload


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
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

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
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

    g = Graph() + model.graph

    return g.serialize(format="ttl"), status.HTTP_200_OK


@blueprint.route("/<models_id>/node_subgraph", methods=(["GET"]))
def get_model_node_subgraph(models_id: int) -> flask.Response:
    """Return the Concise Bounded Description (CBD) of a node within the model graph.

    Query params:
      - node: URI of the node to describe (required)
      - self_contained: boolean (optional; default true). When true, iteratively
        expands the CBD by including CBDs of discovered nodes until convergence.

    :param models_id: model id
    :type models_id: int
    :return: TTL-serialized CBD graph
    :rtype: flask.Response
    """
    try:
        model = Model.load(models_id)
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

    node_param = request.args.get("node")
    if not node_param:
        return {"message": "missing required query parameter 'node'"}, status.HTTP_400_BAD_REQUEST

    self_contained_param = request.args.get("self_contained", "true").lower()
    self_contained = self_contained_param in ("1", "true", "yes", "y", "on")

    try:
        node_ref = URIRef(node_param)
    except Exception:
        return {"message": "invalid 'node' URI"}, status.HTTP_400_BAD_REQUEST

    cbd_graph = model.node_subgraph(node_ref, self_contained=self_contained)
    return cbd_graph.serialize(format="ttl"), status.HTTP_200_OK


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
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

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


@blueprint.route("", methods=(["POST"]))
def create_model() -> flask.Response:
    """Create model

    :return: new model
    :rtype: Model
    """
    if request.content_type != "application/json":
        return {
            "message": "request content type must be json"
        }, status.HTTP_400_BAD_REQUEST

    name = request.json.get("name")
    description = request.json.get("description")

    if name is None:
        return {"message": "must give name"}, status.HTTP_400_BAD_REQUEST

    try:
        model = Model.create(name, description)
    except ValueError:
        return {
            "message": f"{name} does not look like a valid URI, "
            "trying to serialize this will break."
        }, status.HTTP_400_BAD_REQUEST

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
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

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


@blueprint.route("/<models_id>/manifest", methods=(["GET", "POST"]))
def get_model_manifest(models_id: int) -> flask.Response:
    """GET: Return both the manifest body (TTL) and the list of library import URIs (JSON if requested).
       POST: Replace the manifest by either:
         - JSON body with {"library_ids": [...]} to resolve to URIs and set as owl:imports, or
           {"library_uris": [...]} to directly set imports (or both, merged).
         - text/turtle body to replace the manifest graph directly.

    GET behavior:
      - If client requests application/json (Accept header), return:
          {"body": "<ttl string>", "library_uris": ["uri", ...]}
      - Otherwise, return the TTL string as before.

    POST behavior:
      - Content-Type application/json: expects library_ids (ints) and/or library_uris (strings)
      - Content-Type text/turtle: body is a TTL graph to replace the manifest
    """
    try:
        model = Model.load(models_id)
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

    manifest = model.get_manifest()
    g = manifest.graph

    if flask.request.method == "GET":
        ttl_body = g.serialize(format="ttl")
        # Collect all owl:imports objects as URIs
        library_uris = sorted(
            list({str(o) for _, _, o in g.triples((None, OWL.imports, None))})
        )

        # Content negotiation: return JSON only if explicitly requested
        best = request.accept_mimetypes.best_match(
            ["application/json", "text/turtle", "text/plain"]
        )
        if best == "application/json":
            return (
                jsonify({"body": ttl_body, "library_uris": library_uris}),
                status.HTTP_200_OK,
            )
        return ttl_body, status.HTTP_200_OK

    # POST: update/replace manifest
    ct = (request.content_type or "").lower()

    if "application/json" in ct:
        try:
            body = request.json
        except Exception as e:
            return {"message": f"cannot read body {e}"}, status.HTTP_400_BAD_REQUEST

        if not isinstance(body, dict):
            return {"message": "body is not dict"}, status.HTTP_400_BAD_REQUEST

        library_ids = body.get("library_ids", []) or []
        library_uris_in = body.get("library_uris", []) or []

        if not isinstance(library_ids, list) or not all(
            isinstance(x, int) for x in library_ids
        ):
            return {
                "message": "library_ids must be an array of integers"
            }, status.HTTP_400_BAD_REQUEST
        if not isinstance(library_uris_in, list) or not all(
            isinstance(x, str) for x in library_uris_in
        ):
            return {
                "message": "library_uris must be an array of strings"
            }, status.HTTP_400_BAD_REQUEST

        # Resolve library_ids to shape collection identifiers (URIs)
        nonexistent_libraries = []
        resolved_uris = []
        for lib_id in library_ids:
            try:
                db_lib = Library.load(lib_id)
                ident = db_lib.get_shape_collection().graph_name
                if ident is not None:
                    resolved_uris.append(str(ident))
            except LibraryNotFound:
                nonexistent_libraries.append(lib_id)

        if len(nonexistent_libraries) > 0:
            return {
                "message": f"Libraries with ids {nonexistent_libraries} do not exist"
            }, status.HTTP_400_BAD_REQUEST

        # Merge and uniquify URIs, preserving input order
        seen = set()
        import_uris = []
        for uri in resolved_uris + library_uris_in:
            if uri not in seen:
                seen.add(uri)
                import_uris.append(uri)

        # Replace manifest with minimal graph containing owl:imports
        g.remove((None, None, None))
        subject = URIRef(str(model.name))
        for uri in import_uris:
            g.add((subject, OWL.imports, URIRef(uri)))

        current_app.building_motif.session.commit()
        return g.serialize(format="ttl"), status.HTTP_200_OK

    elif "turtle" in ct:
        try:
            new_graph = Graph().parse(data=request.data, format="ttl")
        except BadSyntax as e:
            return {"message": f"data is unreadable: {e}"}, status.HTTP_400_BAD_REQUEST

        g.remove((None, None, None))
        for triple in new_graph:
            g.add(triple)

        current_app.building_motif.session.commit()
        return g.serialize(format="ttl"), status.HTTP_200_OK

    return {
        "message": "Unsupported Content-Type. Use application/json or text/turtle."
    }, status.HTTP_400_BAD_REQUEST


@blueprint.route("/<models_id>/manifest/imports", methods=(["GET", "POST"]))
def manage_manifest_imports(models_id: int) -> flask.Response:
    try:
        model = Model.load(models_id)
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

    manifest = model.get_manifest()
    g = manifest.graph

    # We will encode library IDs as URIs with this prefix
    lib_prefix = "https://nrel.gov/BuildingMOTIF/library/"

    if request.method == "GET":
        library_ids = []
        for _, _, o in g.triples((None, OWL.imports, None)):
            if isinstance(o, URIRef) and str(o).startswith(lib_prefix):
                try:
                    library_ids.append(int(str(o).split("/")[-1]))
                except Exception:
                    continue
        library_ids = sorted(list(set(library_ids)))
        return jsonify({"library_ids": library_ids}), status.HTTP_200_OK

    if request.content_type != "application/json":
        return {
            "message": "request content type must be json"
        }, status.HTTP_400_BAD_REQUEST

    try:
        body = request.json or {}
    except Exception as e:
        return {"message": f"cannot read body {e}"}, status.HTTP_400_BAD_REQUEST

    library_ids = body.get("library_ids", []) or []
    selected_template_ids = body.get("selected_template_ids", []) or []

    # Remove existing imports that match our library prefix
    to_remove = []
    for s, p, o in g.triples((None, OWL.imports, None)):
        if isinstance(o, URIRef) and str(o).startswith(lib_prefix):
            to_remove.append((s, p, o))
    for triple in to_remove:
        g.remove(triple)

    # Use the model's URI as the subject for owl:imports
    subject = URIRef(str(model.name))

    # Add new imports
    for lib_id in library_ids:
        o = URIRef(f"{lib_prefix}{lib_id}")
        g.add((subject, OWL.imports, o))

    current_app.building_motif.session.commit()

    logger.info(f"Selected templates for model {models_id}: {selected_template_ids}")

    return (
        jsonify(
            {"library_ids": library_ids, "selected_template_ids": selected_template_ids}
        ),
        status.HTTP_200_OK,
    )


@blueprint.route("/<models_id>/validate", methods=(["POST"]))
def validate_model(models_id: int) -> flask.Response:
    # get model
    try:
        model = Model.load(models_id)
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

    # parse iteration params
    try:
        min_iterations, max_iterations = _parse_iteration_params()
    except ValueError as e:
        return {"message": str(e)}, status.HTTP_400_BAD_REQUEST

    # determine shape collections
    try:
        shape_collections, nonexistent_libraries = _select_shape_collections(model)
    except ValueError as e:
        return {"message": str(e)}, status.HTTP_400_BAD_REQUEST

    if len(nonexistent_libraries) > 0:
        return {
            "message": f"Libraries with ids {nonexistent_libraries} do not exist"
        }, status.HTTP_400_BAD_REQUEST

    logger.warning(
        f"Validating model {model.name} with shape collections {shape_collections}"
    )

    # compute validation context
    ctx = _compute_validation_context(
        model, shape_collections, min_iterations, max_iterations
    )

    reasons = {
        focus_node: list({gd.reason() for gd in grahdiffs})
        for focus_node, grahdiffs in ctx.diffset.items()
    }

    response = {
        "message": ctx.report_string,
        "valid": ctx.valid,
        "reasons": reasons,
    }

    # optionally include generated templates
    if _parse_bool_param("include_templates", False):
        response["templates"] = _templates_payload_from_context(ctx)

    return response, status.HTTP_200_OK




@blueprint.route("/<models_id>/validate_shape", methods=(["POST"]))
def validate_shape(models_id: int) -> flask.Response:
    # get model
    try:
        model = Model.load(models_id)
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

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
        except ShapeCollectionNotFound:
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
    # Optional SHACL inference iteration parameters
    min_iterations_arg = request.args.get("min_iterations")
    max_iterations_arg = request.args.get("max_iterations")
    min_iterations = 1
    max_iterations = 3
    try:
        if min_iterations_arg is not None:
            min_iterations = int(min_iterations_arg)
        if max_iterations_arg is not None:
            max_iterations = int(max_iterations_arg)
    except ValueError:
        return {"message": "min_iterations and max_iterations must be integers"}, status.HTTP_400_BAD_REQUEST
    if min_iterations < 1 or max_iterations < 1:
        return {"message": "min_iterations and max_iterations must be >= 1"}, status.HTTP_400_BAD_REQUEST

    compiled = model.compile(
        shape_collections,
        min_iterations=min_iterations,
        max_iterations=max_iterations,
    )
    conformance = compiled.validate_model_against_shapes(
        shapes_to_test=shape_uris,
        target_class=target_class,
    )

    result = {}
    for shape_uri, validation_context in conformance.items():
        diffsets = validation_context.diffset.values()
        reasons = [diff.reason() for diffset in diffsets for diff in diffset]
        result[shape_uri] = reasons

    return result, status.HTTP_200_OK


@blueprint.route("/<models_id>/add_manifest_rules", methods=(["POST"]))
def add_fdd_rules_to_manifest(models_id: int) -> flask.Response:
    """Add FDD rules to the model manifest.

    :param models_id: model id
    :type models_id: int
    :return: updated model manifest
    :rtype: flask.Response
    """
    try:
        model = Model.load(models_id)
    except ModelNotFound:
        return {"message": f"ID: {models_id}"}, status.HTTP_404_NOT_FOUND

    # get body
    if request.content_type != "application/json":
        return flask.Response(
            {"message": "request content type must be json"},
            status.HTTP_400_BAD_REQUEST,
        )
    try:
        rules_json = request.json
    except Exception as e:
        return {"message": f"cannot read body {e}"}, status.HTTP_400_BAD_REQUEST

    if not isinstance(rules_json, dict):
        return {"message": "body is not dict"}, status.HTTP_400_BAD_REQUEST

    grouped_diffs, successful_rules, validation_report = generate_report(
        model, rules_json
    )

    return (
        jsonify(
            {
                "grouped_diffs": grouped_diffs,
                "successful_rules": successful_rules,
                "validation_report": validation_report.report.serialize(format="ttl"),
            }
        ),
        status.HTTP_200_OK,
    )
