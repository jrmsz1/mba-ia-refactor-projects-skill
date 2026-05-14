from flask import Blueprint, request, jsonify

from controllers.usuario_controller import UsuarioController
from controllers.produto_controller import ValidationError

usuario_bp = Blueprint("usuario", __name__)


@usuario_bp.route("/usuarios", methods=["GET"])
def listar_usuarios():
    return jsonify({"dados": UsuarioController.list_usuarios(), "sucesso": True}), 200


@usuario_bp.route("/usuarios/<int:id>", methods=["GET"])
def buscar_usuario(id):
    usuario = UsuarioController.get_usuario(id)
    if not usuario:
        return jsonify({"erro": "Usuário não encontrado"}), 404
    return jsonify({"dados": usuario, "sucesso": True}), 200


@usuario_bp.route("/usuarios", methods=["POST"])
def criar_usuario():
    try:
        usuario_id = UsuarioController.create_usuario(request.get_json(silent=True))
    except ValidationError as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201


@usuario_bp.route("/login", methods=["POST"])
def login():
    try:
        usuario = UsuarioController.login(request.get_json(silent=True))
    except ValidationError as exc:
        return jsonify({"erro": str(exc)}), 400
    if not usuario:
        return jsonify({"erro": "Email ou senha inválidos", "sucesso": False}), 401
    return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200
