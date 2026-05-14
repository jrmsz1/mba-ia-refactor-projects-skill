import logging

from flask import jsonify

from controllers.task_controller import ValidationError, NotFoundError
from controllers.user_controller import AuthenticationError

logger = logging.getLogger(__name__)


def register_error_handlers(app):

    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return jsonify({'error': err.message}), err.status_code

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(err):
        return jsonify({'error': err.message}), 404

    @app.errorhandler(AuthenticationError)
    def handle_auth_error(err):
        return jsonify({'error': err.message}), err.status_code

    @app.errorhandler(400)
    def bad_request(err):
        return jsonify({'error': 'Bad request', 'detail': str(getattr(err, 'description', err))}), 400

    @app.errorhandler(404)
    def not_found(err):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(err):
        return jsonify({'error': 'Method not allowed'}), 405

    @app.errorhandler(500)
    def internal_error(err):
        logger.exception('Unhandled 500 error')
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(Exception)
    def unhandled_exception(err):
        logger.exception('Unhandled exception')
        return jsonify({'error': 'Unexpected error'}), 500
