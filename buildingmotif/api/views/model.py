import flask
from flask import Blueprint, current_app, jsonify

from buildingmotif.api.serializers.model import serialize

blueprint = Blueprint("models", __name__)


@blueprint.route("", methods=(["GET"]))
def get_all_models() -> flask.Response:
    """Get all models.

    :return: All models.
    :rtype: List[Model]
    """
    db_models = current_app.building_motif.table_connection.get_all_db_models()

    return jsonify(serialize(db_models))


@blueprint.route("/<models_id>", methods=(["GET"]))
def get_model(models_id: int) -> flask.Response:
    """get model with id

    :param models_id: model id
    :type models_id: int
    :return: requested id
    :rtype: Model
    """
    model = current_app.building_motif.table_connection.get_db_model(models_id)

    return jsonify(serialize(model))
