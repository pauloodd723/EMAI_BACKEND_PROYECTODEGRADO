import random
import string
from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, AccessToken, Institution, UserRoleEnum
from ..schemas import (
    LoginRequest, LoginResponse, RedeemTokenRequest,
    CreateAccountRequest, UpdateProfileRequest,
    UserOut, InstitutionOut,
)
from ..security import (
    verify_password, hash_password,
    create_access_token, get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.patch("/perfil")
async def update_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    body = await request.json()
    full_name = body.get("fullName") or body.get("full_name")
    password = body.get("password")
    photo_url = body.get("photoUrl") or body.get("photo_url")

    if full_name:
        current_user.full_name = full_name.strip()
    if password and len(password) >= 6:
        current_user.password_hash = hash_password(password)
    if photo_url is not None:
        # Guardar el URI de la foto — en producción sería una URL de servidor
        # Por ahora guardamos el URI local/base64
        current_user.photo_url = photo_url

    db.commit()
    db.refresh(current_user)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "fullName": current_user.full_name,
        "role": current_user.role.value,
        "photoUrl": current_user.photo_url,
        "institutionId": current_user.institution_id,
        "updatedAt": current_user.updated_at.isoformat(),
    }
# ─── LOGIN ────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.username == body.username.strip().lower(),
        User.is_active == True,
    ).first()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    token = create_access_token({"sub": user.id})
    institution = db.query(Institution).filter(
        Institution.id == user.institution_id
    ).first() if user.institution_id else None

    return LoginResponse(
        access_token=token,
        user=UserOut.model_validate(user),
        institution=InstitutionOut.model_validate(institution) if institution else None,
    )


# ─── VALIDAR TOKEN DE INSTITUCIÓN ─────────────────────────────────────────────
@router.post("/redeem-token")
def redeem_token(body: RedeemTokenRequest, db: Session = Depends(get_db)):
    token = db.query(AccessToken).filter(
        AccessToken.token == body.token.strip().upper(),
        AccessToken.used == False,
    ).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o ya utilizado",
        )

    return {
        "valid": True,
        "institution_name": token.institution_name,
        "requires_account_creation": True,
    }


# ─── CREAR CUENTA CON TOKEN ───────────────────────────────────────────────────
@router.post("/create-account", response_model=LoginResponse)
def create_account(body: CreateAccountRequest, db: Session = Depends(get_db)):
    # Validar token
    access_token_obj = db.query(AccessToken).filter(
        AccessToken.token == body.token.strip().upper(),
        AccessToken.used == False,
    ).first()

    if not access_token_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o ya utilizado",
        )

    # Verificar que el username no esté tomado
    if db.query(User).filter(User.username == body.username.strip().lower()).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario ya está en uso",
        )

    # Crear institución
    institution = Institution(
        name=access_token_obj.institution_name or "Mi Institución",
        primary_color="#1A3C5E",
        secondary_color="#2E6DA4",
        data_terms_accepted=False,
    )
    db.add(institution)
    db.flush()  # Para obtener el ID

    # Crear usuario directivo principal
    user = User(
        username=body.username.strip().lower(),
        password_hash=hash_password(body.password),
        full_name=body.username.strip(),
        role=UserRoleEnum.directivo,
        sub_role="director",
        institution_id=institution.id,
    )
    db.add(user)
    db.flush()

    # Marcar token como usado
    access_token_obj.used = True
    access_token_obj.used_at = datetime.utcnow()
    access_token_obj.used_by = user.id
    access_token_obj.institution_id = institution.id

    # Crear materia de matemáticas por defecto
    from ..models import Subject
    subject = Subject(
        name="Matemáticas",
        base_type="matematicas",
        institution_id=institution.id,
    )
    db.add(subject)
    db.commit()
    db.refresh(user)
    db.refresh(institution)

    jwt_token = create_access_token({"sub": user.id})
    return LoginResponse(
        access_token=jwt_token,
        user=UserOut.model_validate(user),
        institution=InstitutionOut.model_validate(institution),
    )


# ─── ACTUALIZAR PERFIL ────────────────────────────────────────────────────────
@router.patch("/perfil", response_model=UserOut)
def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.full_name:
        current_user.full_name = body.full_name.strip()
    if body.password:
        current_user.password_hash = hash_password(body.password)
    if body.photo_url is not None:
        current_user.photo_url = body.photo_url

    db.commit()
    db.refresh(current_user)
    return UserOut.model_validate(current_user)
