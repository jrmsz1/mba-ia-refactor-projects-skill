import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from controllers.produto_controller import ValidationError

logger = logging.getLogger(__name__)


def register_error_handlers(app):

    @app.errorhandler(ValidationError)
    def _validation(exc):
        return jsonify({"erro": str(exc), "sucesso": False}), 400

    @app.errorhandler(HTTPException)
    def _http(exc):
        payload = {"erro": exc.name}
        if exc.description and exc.description != exc.name:
            payload["detalhes"] = exc.description
        return jsonify(payload), exc.code

    @app.errorhandler(Exception)
    def _unhandled(exc):
        logger.exception("unhandled exception")
        return jsonify({"erro": "Erro interno do servidor"}), 500
