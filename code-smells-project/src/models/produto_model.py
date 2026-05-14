from models.database import get_db


class ProdutoModel:

    @staticmethod
    def to_dict(row) -> dict:
        return {
            "id": row["id"],
            "nome": row["nome"],
            "descricao": row["descricao"],
            "preco": row["preco"],
            "estoque": row["estoque"],
            "categoria": row["categoria"],
            "ativo": row["ativo"],
            "criado_em": row["criado_em"],
        }

    @staticmethod
    def get_all() -> list[dict]:
        db = get_db()
        rows = db.execute("SELECT * FROM produtos").fetchall()
        return [ProdutoModel.to_dict(r) for r in rows]

    @staticmethod
    def get_by_id(produto_id: int):
        db = get_db()
        row = db.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        return ProdutoModel.to_dict(row) if row else None

    @staticmethod
    def create(nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> int:
        db = get_db()
        cursor = db.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def update(produto_id: int, nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> None:
        db = get_db()
        db.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )
        db.commit()

    @staticmethod
    def delete(produto_id: int) -> None:
        db = get_db()
        db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        db.commit()

    @staticmethod
    def search(termo: str | None, categoria: str | None, preco_min: float | None, preco_max: float | None) -> list[dict]:
        clauses = ["1=1"]
        params: list = []
        if termo:
            clauses.append("(nome LIKE ? OR descricao LIKE ?)")
            like = f"%{termo}%"
            params.extend([like, like])
        if categoria:
            clauses.append("categoria = ?")
            params.append(categoria)
        if preco_min is not None:
            clauses.append("preco >= ?")
            params.append(preco_min)
        if preco_max is not None:
            clauses.append("preco <= ?")
            params.append(preco_max)

        query = "SELECT * FROM produtos WHERE " + " AND ".join(clauses)
        db = get_db()
        rows = db.execute(query, params).fetchall()
        return [ProdutoModel.to_dict(r) for r in rows]

    @staticmethod
    def decrement_estoque(produto_id: int, quantidade: int) -> None:
        db = get_db()
        db.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
            (quantidade, produto_id),
        )
