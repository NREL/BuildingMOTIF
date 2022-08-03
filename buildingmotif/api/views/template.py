import flask
from flask import Blueprint, current_app, jsonify

from buildingmotif.api.serializers.template import serialize

blueprint = Blueprint("templates", __name__)


@blueprint.route("", methods=(["GET"]))
def get_all_templates() -> flask.Response:
    """get all templates

    :return: all templates
    :rtype: List[Template]
    """
    db_templates = current_app.building_motif.table_connection.get_all_db_templates()

    return jsonify(serialize(db_templates))


@blueprint.route("/<templates_id>", methods=(["GET"]))
def get_template(templates_id: int) -> flask.Response:
    """get Template with id

    :param templates_id: template id
    :type templates_id: int
    :return: requested id
    :rtype: Template
    """
    template = current_app.building_motif.table_connection.get_db_template_by_id(
        templates_id
    )

    return jsonify(serialize(template))
