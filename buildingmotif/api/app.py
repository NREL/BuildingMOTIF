from flask import Flask, current_app
from flask_api import status
from sqlalchemy.exc import SQLAlchemyError

from buildingmotif.api.views.library import blueprint as library_blueprint
from buildingmotif.api.views.model import blueprint as model_blueprint
from buildingmotif.api.views.template import blueprint as template_blueprint
from buildingmotif.building_motif.building_motif import BuildingMOTIF


def _after_request(response):
    """Commit or rollback the session.

    :param response: response
    :type response: Flask.response
    :return: response
    :rtype: Flask.response
    """
    try:
        current_app.building_motif.session.commit()
    except SQLAlchemyError:
        current_app.building_motif.session.rollback()

    current_app.building_motif.Session.remove()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response


def _after_error(error):
    """Returns request with a 500 and the error message.

    :param error: python error
    :type error: Error
    :return: flask error response
    :rtype: Flask.response
    """
    return str(error), status.HTTP_500_INTERNAL_SERVER_ERROR


def create_app(DB_URI):
    """Creates a Flask api.

    :param db_uri: db uri
    :type db_uri: str
    :return: Flask app
    :rtype: Flask.app
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DB_URI=DB_URI,
    )
    app.building_motif = BuildingMOTIF(app.config["DB_URI"])

    app.after_request(_after_request)
    app.register_error_handler(Exception, _after_error)

    app.register_blueprint(library_blueprint, url_prefix="/libraries")
    app.register_blueprint(template_blueprint, url_prefix="/templates")
    app.register_blueprint(model_blueprint, url_prefix="/models")

    return app


if __name__ == "__main__":
    """Run api."""
    # If config doesn't exist, this is considered a third party import and module cant be found.
    import configs as building_motif_configs  # type: ignore # isort:skip

    app = create_app(building_motif_configs.DB_URI)
    app.run(debug=True, host="0.0.0.0", threaded=False)
