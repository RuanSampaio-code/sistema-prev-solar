"""
Cria o usuário administrador inicial.
Uso: python -m scripts.seed_admin
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.repositories import user_repository

EMAIL = os.getenv("ADMIN_EMAIL", "admin@prevsolar.com")
PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
NAME = "Administrador"


def main():
    db = SessionLocal()
    try:
        existing = user_repository.get_by_email(db, EMAIL)
        if existing:
            print(f"Usuário {EMAIL} já existe.")
            return
        user = user_repository.create(db, name=NAME, email=EMAIL, hashed_password=hash_password(PASSWORD), role="admin")
        print(f"Admin criado: {user.email} (id={user.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
