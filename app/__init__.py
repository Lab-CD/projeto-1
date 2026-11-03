from flask import Flask

from app.context import load_project
from app.formatting import fmt
from config import DATA_PATH

MAX_REQUEST_BYTES = 1024 * 1024


def create_app(test_config=None):
    application = Flask(__name__)
    application.config.from_mapping(
        DATA_PATH=DATA_PATH,
        MAX_CONTENT_LENGTH=MAX_REQUEST_BYTES,
    )
    if test_config:
        application.config.update(test_config)

    application.extensions["project"] = load_project(application.config["DATA_PATH"])
    application.jinja_env.filters["fmt"] = fmt

    from app.routes import report
    application.register_blueprint(report)
    return application
