import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = _bool("DEBUG", "false")
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))

    DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")

    ADMIN_API_ENABLED = _bool("ADMIN_API_ENABLED", "false")

    CATEGORIAS_VALIDAS = (
        "informatica", "moveis", "vestuario", "geral", "eletronicos", "livros",
    )
    STATUS_PEDIDO_VALIDOS = (
        "pendente", "aprovado", "enviado", "entregue", "cancelado",
    )

    PRODUTO_NOME_MIN_LEN = 2
    PRODUTO_NOME_MAX_LEN = 200

    SALES_REPORT_TIERS = (
        (float(os.environ.get("BULK_DISCOUNT_TIER_1_MIN", "10000")),
         float(os.environ.get("BULK_DISCOUNT_TIER_1_RATE", "0.10"))),
        (float(os.environ.get("BULK_DISCOUNT_TIER_2_MIN", "5000")),
         float(os.environ.get("BULK_DISCOUNT_TIER_2_RATE", "0.05"))),
        (float(os.environ.get("BULK_DISCOUNT_TIER_3_MIN", "1000")),
         float(os.environ.get("BULK_DISCOUNT_TIER_3_RATE", "0.02"))),
    )
