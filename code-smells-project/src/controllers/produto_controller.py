from config.settings import Config
from models.produto_model import ProdutoModel


class ValidationError(Exception):
    pass


class ProdutoController:

    @staticmethod
    def list_produtos() -> list[dict]:
        return ProdutoModel.get_all()

    @staticmethod
    def get_produto(produto_id: int):
        return ProdutoModel.get_by_id(produto_id)

    @staticmethod
    def search_produtos(termo: str, categoria, preco_min, preco_max) -> list[dict]:
        return ProdutoModel.search(termo, categoria, preco_min, preco_max)

    @staticmethod
    def create_produto(data: dict) -> int:
        cleaned = ProdutoController._validate_payload(data, partial=False)
        return ProdutoModel.create(**cleaned)

    @staticmethod
    def update_produto(produto_id: int, data: dict) -> bool:
        existing = ProdutoModel.get_by_id(produto_id)
        if not existing:
            return False
        cleaned = ProdutoController._validate_payload(data, partial=False)
        ProdutoModel.update(produto_id, **cleaned)
        return True

    @staticmethod
    def delete_produto(produto_id: int) -> bool:
        existing = ProdutoModel.get_by_id(produto_id)
        if not existing:
            return False
        ProdutoModel.delete(produto_id)
        return True

    @staticmethod
    def _validate_payload(data: dict | None, partial: bool) -> dict:
        if not data:
            raise ValidationError("Dados inválidos")

        required = ("nome", "preco", "estoque")
        for field, label in zip(required, ("Nome", "Preço", "Estoque")):
            if field not in data:
                raise ValidationError(f"{label} é obrigatório")

        nome = (data.get("nome") or "").strip()
        descricao = data.get("descricao", "")
        preco = data.get("preco")
        estoque = data.get("estoque")
        categoria = data.get("categoria", "geral")

        if not isinstance(preco, (int, float)) or isinstance(preco, bool):
            raise ValidationError("Preço deve ser numérico")
        if preco < 0:
            raise ValidationError("Preço não pode ser negativo")
        if not isinstance(estoque, int) or isinstance(estoque, bool):
            raise ValidationError("Estoque deve ser inteiro")
        if estoque < 0:
            raise ValidationError("Estoque não pode ser negativo")
        if len(nome) < Config.PRODUTO_NOME_MIN_LEN:
            raise ValidationError("Nome muito curto")
        if len(nome) > Config.PRODUTO_NOME_MAX_LEN:
            raise ValidationError("Nome muito longo")
        if categoria not in Config.CATEGORIAS_VALIDAS:
            raise ValidationError(
                f"Categoria inválida. Válidas: {list(Config.CATEGORIAS_VALIDAS)}"
            )

        return {
            "nome": nome,
            "descricao": descricao,
            "preco": float(preco),
            "estoque": int(estoque),
            "categoria": categoria,
        }
