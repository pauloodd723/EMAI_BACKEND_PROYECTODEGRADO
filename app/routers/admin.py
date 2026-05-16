import random
import string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import User, AccessToken, Institution, SupportMessage, UserRoleEnum
from ..schemas import AdminStats, AccessTokenOut, UserOut, SupportMessageOut
from ..security import require_role, hash_password, get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])
require_admin = require_role(UserRoleEnum.admin)


def _gen_token() -> str:
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(random.choices(chars, k=4))
    part2 = ''.join(random.choices(chars, k=4))
    return f"EMAI-{part1}-{part2}"


# ─── STATS ───────────────────────────────────────────────────────────────────
@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return {
        "totalTokens": db.query(AccessToken).count(),
        "tokensUsados": db.query(AccessToken).filter(AccessToken.used == True).count(),
        "totalInstituciones": db.query(Institution).count(),
        "totalAdmins": db.query(User).filter(User.role == UserRoleEnum.admin).count(),
        "mensajesSinLeer": db.query(SupportMessage).filter(SupportMessage.read == False).count(),
    }


# ─── TOKENS ──────────────────────────────────────────────────────────────────
@router.get("/tokens", response_model=list[AccessTokenOut])
def list_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return db.query(AccessToken).order_by(AccessToken.created_at.desc()).all()


@router.post("/tokens", response_model=AccessTokenOut, status_code=201)
async def create_token(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    body = await request.json()
    institution_name = body.get("institutionName") or body.get("institution_name")

    for _ in range(10):
        candidate = _gen_token()
        if not db.query(AccessToken).filter(AccessToken.token == candidate).first():
            break
    else:
        raise HTTPException(status_code=500, detail="No se pudo generar un token único")

    token = AccessToken(
        token=candidate,
        institution_name=institution_name,
        created_by=current_user.id,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


# ─── ADMINISTRADORES ─────────────────────────────────────────────────────────
@router.get("/admins", response_model=list[UserOut])
def list_admins(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return db.query(User).filter(User.role == UserRoleEnum.admin).all()


@router.post("/admins", status_code=201)
async def create_admin(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    body = await request.json()
    username = (body.get("username") or "").strip().lower()
    password = body.get("password") or ""
    full_name = body.get("fullName") or body.get("full_name") or username

    if not username or not password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña son requeridos")

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener mínimo 6 caracteres")

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="El nombre de usuario ya está en uso")

    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=UserRoleEnum.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "fullName": user.full_name,
        "role": user.role.value,
        "createdAt": user.created_at.isoformat(),
    }


@router.delete("/admins/{user_id}", status_code=204)
def delete_admin(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")

    user = db.query(User).filter(User.id == user_id, User.role == UserRoleEnum.admin).first()
    if not user:
        raise HTTPException(status_code=404, detail="Administrador no encontrado")

    db.delete(user)
    db.commit()


# ─── SOPORTE ─────────────────────────────────────────────────────────────────
@router.get("/soporte", response_model=list[SupportMessageOut])
def list_support(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return db.query(SupportMessage).order_by(SupportMessage.created_at.desc()).all()


@router.patch("/soporte/{msg_id}/leer", status_code=200)
def mark_read(
    msg_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    msg = db.query(SupportMessage).filter(SupportMessage.id == msg_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    msg.read = True
    db.commit()
    return {"ok": True}
