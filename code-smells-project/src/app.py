import logging
import os
import sys

# Allow `python src/app.py` from project root: ensure `src/` is on sys.path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_cors import CORS

from config.settings import Config
from middlewares.error_handler import register_error_handlers
from models.database import init_app as init_db
from views.admin_routes import admin_bp
from views.health_routes import health_bp
from views.index_routes import index_bp
from views.pedido_routes import pedido_bp
from views.produto_routes import produto_bp
from views.relatorio_routes import relatorio_bp
from views.usuario_routes import usuario_bp


def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)
    CORS(app)

    init_db(app)

    app.register_blueprint(index_bp)
    app.register_blueprint(produto_bp)
    app.register_blueprint(usuario_bp)
    app.register_blueprint(pedido_bp)
    app.register_blueprint(relatorio_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(admin_bp)

    register_error_handlers(app)
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = create_app()
    print("=" * 50)
    print("SERVIDOR INICIADO")
    print(f"Rodando em http://{Config.HOST}:{Config.PORT}")
    print("=" * 50)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
