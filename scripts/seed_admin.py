"""
Script de seed inicial.
Crea el primer usuario administrador del sistema.

Uso:
    python -m scripts.seed_admin
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, UserRoleEnum, Base
from app.database import engine
from app.security import hash_password

def seed_admin():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.role == UserRoleEnum.admin).first()
        if existing:
            print(f"✓ Admin ya existe: @{existing.username}")
            return

        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            full_name="Administrador EMAI",
            role=UserRoleEnum.admin,
        )
        db.add(admin)
        db.commit()
        print("✓ Admin creado:")
        print("  Usuario: admin")
        print("  Contraseña: admin123")
        print("  ⚠ Cambia la contraseña inmediatamente en producción")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
