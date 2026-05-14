from flask import Blueprint, request, jsonify

from controllers.produto_controller import ProdutoController, ValidationError

produto_bp = Blueprint("produto", __name__, url_prefix="/produtos")


@produto_bp.route("", methods=["GET"])
def listar_produtos():
    produtos = ProdutoController.list_produtos()
    return jsonify({"dados": produtos, "sucesso": True}), 200


@produto_bp.route("/busca", methods=["GET"])
def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria")
    preco_min = request.args.get("preco_min", type=float)
    preco_max = request.args.get("preco_max", type=float)
    resultados = ProdutoController.search_produtos(termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200


@produto_bp.route("/<int:id>", methods=["GET"])
def buscar_produto(id):
    produto = ProdutoController.get_produto(id)
    if not produto:
        return jsonify({"erro": "Produto não encontrado", "sucesso": False}), 404
    return jsonify({"dados": produto, "sucesso": True}), 200


@produto_bp.route("", methods=["POST"])
def criar_produto():
    try:
        produto_id = ProdutoController.create_produto(request.get_json(silent=True))
    except ValidationError as exc:
        return jsonify({"erro": str(exc)}), 400
    return jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}), 201


@produto_bp.route("/<int:id>", methods=["PUT"])
def atualizar_produto(id):
    try:
        ok = ProdutoController.update_produto(id, request.get_json(silent=True))
    except ValidationError as exc:
        return jsonify({"erro": str(exc)}), 400
    if not ok:
        return jsonify({"erro": "Produto não encontrado"}), 404
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


@produto_bp.route("/<int:id>", methods=["DELETE"])
def deletar_produto(id):
    ok = ProdutoController.delete_produto(id)
    if not ok:
        return jsonify({"erro": "Produto não encontrado"}), 404
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
