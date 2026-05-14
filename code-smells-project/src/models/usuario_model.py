from models.database import get_db


class UsuarioModel:

    @staticmethod
    def to_public_dict(row) -> dict:
        return {
            "id": row["id"],
            "nome": row["nome"],
            "email": row["email"],
            "tipo": row["tipo"],
            "criado_em": row["criado_em"],
        }

    @staticmethod
    def get_all() -> list[dict]:
        db = get_db()
        rows = db.execute(
            "SELECT id, nome, email, tipo, criado_em FROM usuarios"
        ).fetchall()
        return [UsuarioModel.to_public_dict(r) for r in rows]

    @staticmethod
    def get_by_id(usuario_id: int):
        db = get_db()
        row = db.execute(
            "SELECT id, nome, email, tipo, criado_em FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        return UsuarioModel.to_public_dict(row) if row else None

    @staticmethod
    def get_by_email_with_password(email: str):
        db = get_db()
        return db.execute(
            "SELECT id, nome, email, senha, tipo FROM usuarios WHERE email = ?",
            (email,),
        ).fetchone()

    @staticmethod
    def create(nome: str, email: str, senha_hash: str, tipo: str = "cliente") -> int:
        db = get_db()
        cursor = db.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, tipo),
        )
        db.commit()
        return cursor.lastrowid
