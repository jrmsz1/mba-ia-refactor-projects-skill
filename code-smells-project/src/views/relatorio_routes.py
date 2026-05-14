from flask import Blueprint, jsonify

from controllers.relatorio_controller import RelatorioController

relatorio_bp = Blueprint("relatorio", __name__, url_prefix="/relatorios")


@relatorio_bp.route("/vendas", methods=["GET"])
def relatorio_vendas():
    return jsonify({"dados": RelatorioController.build_sales_report(), "sucesso": True}), 200
