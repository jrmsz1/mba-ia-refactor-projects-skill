import logging

from config.settings import Config
from controllers.produto_controller import ValidationError
from models.database import get_db
from models.pedido_model import PedidoModel
from models.produto_model import ProdutoModel

logger = logging.getLogger(__name__)


class PedidoController:

    @staticmethod
    def process_checkout(data: dict | None) -> dict:
        if not data:
            raise ValidationError("Dados inválidos")
        usuario_id = data.get("usuario_id")
        itens = data.get("itens", [])
        if not usuario_id:
            raise ValidationError("Usuario ID é obrigatório")
        if not itens:
            raise ValidationError("Pedido deve ter pelo menos 1 item")

        produtos: list[tuple[dict, int]] = []
        total = 0.0
        for item in itens:
            produto = ProdutoModel.get_by_id(item.get("produto_id"))
            if produto is None:
                raise ValidationError(
                    f"Produto {item.get('produto_id')} não encontrado"
                )
            quantidade = int(item.get("quantidade", 0))
            if quantidade <= 0:
                raise ValidationError(
                    f"Quantidade inválida para {produto['nome']}"
                )
            if produto["estoque"] < quantidade:
                raise ValidationError(
                    f"Estoque insuficiente para {produto['nome']}"
                )
            produtos.append((produto, quantidade))
            total += produto["preco"] * quantidade

        db = get_db()
        try:
            pedido_id = PedidoModel.create(usuario_id=usuario_id, total=total)
            for produto, quantidade in produtos:
                PedidoModel.add_item(
                    pedido_id=pedido_id,
                    produto_id=produto["id"],
                    quantidade=quantidade,
                    preco_unitario=produto["preco"],
                )
                ProdutoModel.decrement_estoque(produto["id"], quantidade)
            db.commit()
        except Exception:
            db.rollback()
            raise

        PedidoController._notify_order_created(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": round(total, 2)}

    @staticmethod
    def list_pedidos_usuario(usuario_id: int) -> list[dict]:
        return PedidoModel.get_by_usuario(usuario_id)

    @staticmethod
    def list_all_pedidos() -> list[dict]:
        return PedidoModel.get_all()

    @staticmethod
    def update_status(pedido_id: int, novo_status: str) -> None:
        if novo_status not in Config.STATUS_PEDIDO_VALIDOS:
            raise ValidationError("Status inválido")
        PedidoModel.update_status(pedido_id, novo_status)
        PedidoController._notify_status_change(pedido_id, novo_status)

    @staticmethod
    def _notify_order_created(pedido_id: int, usuario_id: int) -> None:
        logger.info("notify.order_created pedido=%s usuario=%s", pedido_id, usuario_id)

    @staticmethod
    def _notify_status_change(pedido_id: int, status: str) -> None:
        if status == "aprovado":
            logger.info("notify.order_approved pedido=%s", pedido_id)
        elif status == "cancelado":
            logger.info("notify.order_cancelled pedido=%s", pedido_id)
