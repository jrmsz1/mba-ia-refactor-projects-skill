from flask import Blueprint, request, jsonify, abort

from config.settings import Config
from models.database import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
def _gate_admin():
    if not Config.ADMIN_API_ENABLED:
        abort(404)


@admin_bp.route("/reset-db", methods=["POST"])
def reset_database():
    db = get_db()
    db.execute("DELETE FROM itens_pedido")
    db.execute("DELETE FROM pedidos")
    db.execute("DELETE FROM produtos")
    db.execute("DELETE FROM usuarios")
    db.commit()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


@admin_bp.route("/query", methods=["POST"])
def executar_query():
    dados = request.get_json(silent=True) or {}
    query = dados.get("sql", "")
    if not query:
        return jsonify({"erro": "Query não informada"}), 400

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(query)
        if query.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            return jsonify({"dados": [dict(r) for r in rows], "sucesso": True}), 200
        db.commit()
        return jsonify({"mensagem": "Query executada", "sucesso": True}), 200
    except Exception as exc:
        return jsonify({"erro": str(exc)}), 500
