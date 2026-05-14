from models.database import get_db


class PedidoModel:

    @staticmethod
    def to_dict(row) -> dict:
        return {
            "id": row["id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": [],
        }

    @staticmethod
    def create(usuario_id: int, total: float, status: str = "pendente") -> int:
        db = get_db()
        cursor = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, status, total),
        )
        return cursor.lastrowid

    @staticmethod
    def add_item(pedido_id: int, produto_id: int, quantidade: int, preco_unitario: float) -> None:
        db = get_db()
        db.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            (pedido_id, produto_id, quantidade, preco_unitario),
        )

    @staticmethod
    def update_status(pedido_id: int, novo_status: str) -> None:
        db = get_db()
        db.execute(
            "UPDATE pedidos SET status = ? WHERE id = ?",
            (novo_status, pedido_id),
        )
        db.commit()

    @staticmethod
    def get_by_usuario(usuario_id: int) -> list[dict]:
        return PedidoModel._fetch_with_items(
            "WHERE p.usuario_id = ?", (usuario_id,)
        )

    @staticmethod
    def get_all() -> list[dict]:
        return PedidoModel._fetch_with_items("", ())

    @staticmethod
    def _fetch_with_items(where_clause: str, params: tuple) -> list[dict]:
        db = get_db()
        query = f"""
            SELECT p.id AS pedido_id, p.usuario_id, p.status, p.total, p.criado_em,
                   i.produto_id, i.quantidade, i.preco_unitario,
                   pr.nome AS produto_nome
            FROM pedidos p
            LEFT JOIN itens_pedido i ON i.pedido_id = p.id
            LEFT JOIN produtos pr ON pr.id = i.produto_id
            {where_clause}
            ORDER BY p.id
        """
        rows = db.execute(query, params).fetchall()

        pedidos: dict[int, dict] = {}
        for row in rows:
            pid = row["pedido_id"]
            if pid not in pedidos:
                pedidos[pid] = {
                    "id": pid,
                    "usuario_id": row["usuario_id"],
                    "status": row["status"],
                    "total": row["total"],
                    "criado_em": row["criado_em"],
                    "itens": [],
                }
            if row["produto_id"] is not None:
                pedidos[pid]["itens"].append({
                    "produto_id": row["produto_id"],
                    "produto_nome": row["produto_nome"] or "Desconhecido",
                    "quantidade": row["quantidade"],
                    "preco_unitario": row["preco_unitario"],
                })
        return list(pedidos.values())

    @staticmethod
    def get_sales_aggregates() -> dict:
        db = get_db()
        row = db.execute(
            """
            SELECT
                COUNT(*) AS total_pedidos,
                COALESCE(SUM(total), 0) AS faturamento,
                SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END) AS pendentes,
                SUM(CASE WHEN status = 'aprovado' THEN 1 ELSE 0 END) AS aprovados,
                SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END) AS cancelados
            FROM pedidos
            """
        ).fetchone()
        return {
            "total_pedidos": row["total_pedidos"] or 0,
            "faturamento": row["faturamento"] or 0.0,
            "pendentes": row["pendentes"] or 0,
            "aprovados": row["aprovados"] or 0,
            "cancelados": row["cancelados"] or 0,
        }
