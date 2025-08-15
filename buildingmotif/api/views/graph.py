import flask
from flask import Blueprint, current_app
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

    return g.serialize(format="ttl"), status.HTTP_200_OK
