import random
import string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import User, AccessToken, Course, Institution, SupportMessage, UserRoleEnum
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

@router.get("/instituciones")
def list_instituciones(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Lista todas las instituciones con stats básicos."""
    instituciones = db.query(Institution).order_by(Institution.name).all()
    result = []
    for inst in instituciones:
        total_users = db.query(User).filter(
            User.institution_id == inst.id,
            User.is_active == True,
            User.role.in_([UserRoleEnum.docente, UserRoleEnum.directivo]),
        ).count()
        docentes = db.query(User).filter(
            User.institution_id == inst.id,
            User.is_active == True,
            User.role == UserRoleEnum.docente,
        ).count()
        directivos = db.query(User).filter(
            User.institution_id == inst.id,
            User.is_active == True,
            User.role == UserRoleEnum.directivo,
        ).count()
        cursos = db.query(Course).filter(Course.institution_id == inst.id).count()
        result.append({
            "id": inst.id,
            "name": inst.name,
            "token": inst.token if hasattr(inst, "token") else None,
            "totalUsuarios": total_users,
            "docentes": docentes,
            "directivos": directivos,
            "cursos": cursos,
            "createdAt": inst.created_at.isoformat() if hasattr(inst, "created_at") else None,
        })
    return result


@router.get("/instituciones/{inst_id}/usuarios")
def list_usuarios_institucion(
    inst_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Lista directivos y docentes de una institución."""
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institución no encontrada")

    usuarios = db.query(User).filter(
        User.institution_id == inst_id,
        User.is_active == True,
        User.role.in_([UserRoleEnum.docente, UserRoleEnum.directivo]),
    ).order_by(User.role, User.full_name).all()

    result = []
    for u in usuarios:
        # Buscar curso asignado si es docente
        curso_asignado = None
        if u.role == UserRoleEnum.docente:
            curso = db.query(Course).filter(Course.teacher_id == u.id).first()
            if curso:
                curso_asignado = {
                    "id": curso.id,
                    "name": curso.name,
                    "grade": curso.grade,
                    "group": curso.group,
                }
        result.append({
            "id": u.id,
            "username": u.username,
            "fullName": u.full_name,
            "role": u.role.value,
            "photoUrl": u.photo_url,
            "cursoAsignado": curso_asignado,
            "createdAt": u.created_at.isoformat(),
        })
    return result


@router.delete("/usuarios/{user_id}", status_code=204)
def eliminar_usuario(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Desactiva un docente o directivo.
    Sus cursos quedan sin docente asignado; exámenes y resultados se conservan.
    """
    usuario = db.query(User).filter(
        User.id == user_id,
        User.is_active == True,
        User.role.in_([UserRoleEnum.docente, UserRoleEnum.directivo]),
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Desasignar cursos que tenía asignados
    for curso in db.query(Course).filter(Course.teacher_id == usuario.id).all():
        curso.teacher_id = None

    usuario.is_active = False
    db.commit()


@router.post("/instituciones/{inst_id}/usuarios", status_code=201)
async def crear_usuario_institucion(
    inst_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Crea un nuevo docente o directivo en una institución."""
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institución no encontrada")

    body = await request.json()
    username  = (body.get("username") or "").strip().lower()
    password  = body.get("password") or ""
    full_name = (body.get("fullName") or body.get("full_name") or username).strip()
    role_str  = (body.get("role") or "").strip().lower()

    if not username or not password or not role_str:
        raise HTTPException(status_code=400, detail="Usuario, contraseña y rol son requeridos")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener mínimo 6 caracteres")
    if role_str not in ("docente", "directivo"):
        raise HTTPException(status_code=400, detail="Rol inválido. Use 'docente' o 'directivo'")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="El nombre de usuario ya está en uso")

    role = UserRoleEnum.docente if role_str == "docente" else UserRoleEnum.directivo
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        institution_id=inst_id,
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


@router.patch("/usuarios/{user_id}/rol")
async def cambiar_rol_usuario(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Cambia el rol de un usuario (docente ↔ directivo).
    
    Efectos:
    - Si era docente: desasigna su curso (teacher_id = NULL)
    - Si tenía sesión activa: se invalida (updated_at se actualiza,
      el token JWT anterior queda huérfano por tiempo de vida)
    - El curso queda sin profesor hasta nueva asignación
    - El nuevo rol determina qué panel ve el usuario al hacer login
    """
    body = await request.json()
    new_role_str = (body.get("role") or "").strip().lower()

    if new_role_str not in ("docente", "directivo"):
        raise HTTPException(status_code=400, detail="Rol inválido. Use 'docente' o 'directivo'")

    usuario = db.query(User).filter(
        User.id == user_id,
        User.is_active == True,
    ).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # No permitir cambiar rol del propio admin
    if usuario.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes cambiar tu propio rol")

    # No operar sobre admins
    if usuario.role == UserRoleEnum.admin:
        raise HTTPException(status_code=400, detail="No se puede cambiar el rol de un administrador")

    new_role = UserRoleEnum.docente if new_role_str == "docente" else UserRoleEnum.directivo
    old_role = usuario.role

    # Si cambia DE docente: desasignar curso
    if old_role == UserRoleEnum.docente and new_role != UserRoleEnum.docente:
        cursos = db.query(Course).filter(Course.teacher_id == usuario.id).all()
        for curso in cursos:
            curso.teacher_id = None  # curso queda sin profesor

    # Si cambia A docente desde directivo: no asignar curso automáticamente
    # (el directivo/admin lo asignará manualmente)

    # Cambiar rol
    usuario.role = new_role

    # Invalidar sesión activa: actualizar updated_at fuerza que el token
    # anterior quede con claims desactualizados (si el backend verifica updated_at)
    # Como mínimo, el usuario deberá hacer login de nuevo para ver el nuevo panel
    from datetime import datetime
    usuario.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(usuario)

    return {
        "id": usuario.id,
        "username": usuario.username,
        "fullName": usuario.full_name,
        "rolAnterior": old_role.value,
        "rolNuevo": usuario.role.value,
        "cursosDesasignados": old_role == UserRoleEnum.docente and new_role != UserRoleEnum.docente,
        "mensaje": f"Rol cambiado a {new_role.value}. El usuario deberá iniciar sesión nuevamente."
    }
