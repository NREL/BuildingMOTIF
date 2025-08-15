import flask
from flask import Blueprint, current_app, request
from flask_api import status
from rdflib import Graph

blueprint = Blueprint("graph", __name__)


@blueprint.route("/<path:graph_id>", methods=(["GET"]))
def get_graph_by_id(graph_id: str) -> flask.Response:
    """Get an RDF graph by its identifier.

    Accepts any graph identifier string (including URIs with slashes).
    Returns a Turtle serialization of the graph if found.

    :param graph_id: the identifier of the graph to retrieve
    :type graph_id: str
    :return: Turtle-serialized graph or 404 if not found
    :rtype: flask.Response
    """
    try:
        g = current_app.building_motif.graph_connection.get_graph(graph_id)
    except Exception:
        current_app.logger.error(f"Graph with ID {graph_id} not found.", exc_info=True)
        return {"message": f"ID: {graph_id}"}, status.HTTP_404_NOT_FOUND

    # the graph_connection API returns an empty graph if the ID is not found. This
    # is helpful when we are creating models and shape collections and templates, but
    # here we want to return a 404 if the graph is not found.
    if len(g) == 0:
        current_app.logger.warning(f"Graph with ID {graph_id} not found.", exc_info=True)
        return {"message": f"ID: {graph_id}"}, status.HTTP_404_NOT_FOUND

    # Negotiate serialization format based on Content-Type (and fallback to Accept), defaulting to Turtle
    mime_to_format = {
        "text/turtle": ("turtle", "text/turtle"),
        "application/x-turtle": ("turtle", "text/turtle"),
        "application/ld+json": ("json-ld", "application/ld+json"),
        "application/json": ("json-ld", "application/ld+json"),
        "application/rdf+xml": ("xml", "application/rdf+xml"),
        "application/n-triples": ("nt", "application/n-triples"),
        "text/plain": ("nt", "application/n-triples"),
        "text/n3": ("n3", "text/n3"),
        "application/n-quads": ("nquads", "application/n-quads"),
        "application/trig": ("trig", "application/trig"),
    }

    header_ct = (request.headers.get("Content-Type") or "").strip().lower()
    header_accept = (request.headers.get("Accept") or "").strip().lower()

    def pick_mime(h: str) -> str:
        if not h:
            return ""
        # choose the first media type, strip parameters
        first = h.split(",")[0].strip()
        return first.split(";")[0].strip()

    desired_mime = pick_mime(header_ct) or pick_mime(header_accept)
    fmt, out_mime = mime_to_format.get(desired_mime, ("turtle", "text/turtle"))

    data = g.serialize(format=fmt)
    return flask.Response(data, status=status.HTTP_200_OK, mimetype=out_mime)
