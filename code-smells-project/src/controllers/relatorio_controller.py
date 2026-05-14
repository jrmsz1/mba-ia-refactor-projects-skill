from config.settings import Config
from models.pedido_model import PedidoModel


class RelatorioController:

    @staticmethod
    def build_sales_report() -> dict:
        agg = PedidoModel.get_sales_aggregates()
        faturamento = float(agg["faturamento"])
        total_pedidos = int(agg["total_pedidos"])

        desconto = 0.0
        for threshold, rate in Config.SALES_REPORT_TIERS:
            if faturamento > threshold:
                desconto = faturamento * rate
                break

        ticket_medio = (faturamento / total_pedidos) if total_pedidos > 0 else 0.0

        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": int(agg["pendentes"]),
            "pedidos_aprovados": int(agg["aprovados"]),
            "pedidos_cancelados": int(agg["cancelados"]),
            "ticket_medio": round(ticket_medio, 2),
        }
