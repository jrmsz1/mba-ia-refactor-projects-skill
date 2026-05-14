import bcrypt

from models.usuario_model import UsuarioModel
from controllers.produto_controller import ValidationError


class UsuarioController:

    @staticmethod
    def list_usuarios() -> list[dict]:
        return UsuarioModel.get_all()

    @staticmethod
    def get_usuario(usuario_id: int):
        return UsuarioModel.get_by_id(usuario_id)

    @staticmethod
    def create_usuario(data: dict | None) -> int:
        if not data:
            raise ValidationError("Dados inválidos")
        nome = (data.get("nome") or "").strip()
        email = (data.get("email") or "").strip()
        senha = data.get("senha") or ""

        if not nome or not email or not senha:
            raise ValidationError("Nome, email e senha são obrigatórios")

        senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        return UsuarioModel.create(nome, email, senha_hash)

    @staticmethod
    def login(data: dict | None):
        if not data:
            raise ValidationError("Email e senha são obrigatórios")
        email = (data.get("email") or "").strip()
        senha = data.get("senha") or ""
        if not email or not senha:
            raise ValidationError("Email e senha são obrigatórios")

        row = UsuarioModel.get_by_email_with_password(email)
        if not row:
            return None
        stored = row["senha"] or ""
        try:
            ok = bcrypt.checkpw(senha.encode("utf-8"), stored.encode("utf-8"))
        except ValueError:
            ok = False
        if not ok:
            return None
        return {
            "id": row["id"],
            "nome": row["nome"],
            "email": row["email"],
            "tipo": row["tipo"],
        }
