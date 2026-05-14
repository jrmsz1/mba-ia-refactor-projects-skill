from flask import Blueprint, request, jsonify

from controllers.pedido_controller import PedidoController
from controllers.produto_controller import ValidationError

pedido_bp = Blueprint("pedido", __name__, url_prefix="/pedidos")


@pedido_bp.route("", methods=["POST"])
def criar_pedido():
    try:
        resultado = PedidoController.process_checkout(request.get_json(silent=True))
    except ValidationError as exc:
        return jsonify({"erro": str(exc), "sucesso": False}), 400
    return jsonify({
        "dados": resultado,
        "sucesso": True,
        "mensagem": "Pedido criado com sucesso",
    }), 201


@pedido_bp.route("", methods=["GET"])
def listar_todos_pedidos():
    return jsonify({"dados": PedidoController.list_all_pedidos(), "sucesso": True}), 200


@pedido_bp.route("/usuario/<int:usuario_id>", methods=["GET"])
def listar_pedidos_usuario(usuario_id):
    pedidos = PedidoController.list_pedidos_usuario(usuario_id)
    return jsonify({"dados": pedidos, "sucesso": True}), 200


@pedido_bp.route("/<int:pedido_id>/status", methods=["PUT"])
def atualizar_status_pedido(pedido_id):
    data = request.get_json(silent=True) or {}
    novo_status = data.get("status", "")
    try:
        PedidoController.update_status(pedido_id, novo_status)
    except ValidationError as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
