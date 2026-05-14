from flask import Blueprint, jsonify

from models.database import get_db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    try:
        db = get_db()
        produtos = db.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
        usuarios = db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        pedidos = db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    except Exception as exc:
        return jsonify({"status": "erro", "detalhes": str(exc)}), 500

    return jsonify({
        "status": "ok",
        "database": "connected",
        "counts": {
            "produtos": produtos,
            "usuarios": usuarios,
            "pedidos": pedidos,
        },
        "versao": "1.0.0",
    }), 200
