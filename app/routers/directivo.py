from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Institution, Course, Subject, Student, UserRoleEnum, DirectivoSubRoleEnum
from ..security import hash_password, get_current_user

router = APIRouter(prefix="/directivo", tags=["directivo"])


def _check_institution(current_user: User) -> str:
    if not current_user.institution_id:
        raise HTTPException(status_code=400, detail="Usuario sin institución asignada")
    return current_user.institution_id


# ─── STATS ───────────────────────────────────────────────────────────────────
@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    return {
        "totalDirectivos": db.query(User).filter(
            User.institution_id == inst_id, User.role == UserRoleEnum.directivo
        ).count(),
        "totalDocentes": db.query(User).filter(
            User.institution_id == inst_id, User.role == UserRoleEnum.docente
        ).count(),
        "totalCursos": db.query(Course).filter(Course.institution_id == inst_id).count(),
        "totalEstudiantes": db.query(Student).filter(Student.institution_id == inst_id).count(),
    }


# ─── INSTITUCIÓN ─────────────────────────────────────────────────────────────
@router.patch("/institucion")
async def update_institution(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    institution = db.query(Institution).filter(Institution.id == inst_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institución no encontrada")

    body = await request.json()
    name = body.get("name")
    primary_color = body.get("primaryColor") or body.get("primary_color")
    secondary_color = body.get("secondaryColor") or body.get("secondary_color")
    data_terms = body.get("dataTermsAccepted")

    if name:
        institution.name = name.strip()
    if primary_color:
        institution.primary_color = primary_color
    if secondary_color:
        institution.secondary_color = secondary_color
    if data_terms is not None:
        institution.data_terms_accepted = bool(data_terms)

    db.commit()
    db.refresh(institution)
    return {
        "id": institution.id,
        "name": institution.name,
        "primaryColor": institution.primary_color,
        "secondaryColor": institution.secondary_color,
        "dataTermsAccepted": institution.data_terms_accepted,
        "createdAt": institution.created_at.isoformat(),
        "updatedAt": institution.updated_at.isoformat(),
    }


# ─── USUARIOS ────────────────────────────────────────────────────────────────
@router.get("/usuarios")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    users = db.query(User).filter(
        User.institution_id == inst_id,
        User.role.in_([UserRoleEnum.directivo, UserRoleEnum.docente]),
        User.is_active == True,
    ).order_by(User.role, User.full_name).all()
    return [_user_to_dict(u) for u in users]


@router.post("/usuarios", status_code=201)
async def create_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    body = await request.json()

    username = (body.get("username") or "").strip().lower()
    password = body.get("password") or ""
    full_name = body.get("fullName") or body.get("full_name") or username
    role_str = body.get("role") or "docente"
    sub_role_str = body.get("subRole") or body.get("sub_role")
    course_id = body.get("courseId") or body.get("course_id")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña son requeridos")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Mínimo 6 caracteres")
    if len(username) < 4:
        raise HTTPException(status_code=400, detail="Usuario mínimo 4 caracteres")

    try:
        role = UserRoleEnum(role_str)
    except ValueError:
        role = UserRoleEnum.docente

    if role == UserRoleEnum.admin:
        raise HTTPException(status_code=403, detail="No se puede crear admin desde aquí")

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="El nombre de usuario ya está en uso")

    sub_role = None
    if sub_role_str:
        try:
            sub_role = DirectivoSubRoleEnum(sub_role_str)
        except ValueError:
            sub_role = None

    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        sub_role=sub_role,
        institution_id=inst_id,
        course_id=course_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_to_dict(user)


@router.patch("/usuarios/{user_id}")
async def update_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    user = db.query(User).filter(User.id == user_id, User.institution_id == inst_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    body = await request.json()
    full_name = body.get("fullName") or body.get("full_name")
    password = body.get("password")
    sub_role_str = body.get("subRole") or body.get("sub_role")
    course_id = body.get("courseId") or body.get("course_id")
    photo_url = body.get("photoUrl") or body.get("photo_url")

    if full_name:
        user.full_name = full_name.strip()
    if password and len(password) >= 6:
        user.password_hash = hash_password(password)
    if sub_role_str is not None:
        try:
            user.sub_role = DirectivoSubRoleEnum(sub_role_str)
        except ValueError:
            pass
    if course_id is not None:
        user.course_id = course_id
    if photo_url is not None:
        user.photo_url = photo_url

    db.commit()
    db.refresh(user)
    return _user_to_dict(user)


# ─── CURSOS ──────────────────────────────────────────────────────────────────
@router.get("/cursos")
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    courses = db.query(Course).filter(
        Course.institution_id == inst_id
    ).order_by(Course.grade, Course.group).all()
    return [_course_to_dict(c) for c in courses]


@router.post("/cursos", status_code=201)
async def create_course(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    body = await request.json()
    grade = (body.get("grade") or "").strip()
    group = (body.get("group") or "").strip()
    name = body.get("name") or f"{grade}-{group}"

    if not grade or not group:
        raise HTTPException(status_code=400, detail="Grado y grupo son requeridos")

    course = Course(name=name, grade=grade, group=group, institution_id=inst_id)
    db.add(course)
    db.commit()
    db.refresh(course)
    return _course_to_dict(course)


@router.patch("/cursos/{course_id}/asignar")
async def assign_teacher(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.institution_id == inst_id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    body = await request.json()
    teacher_id = body.get("teacherId") or body.get("teacher_id") or None
    course.teacher_id = teacher_id
    db.commit()
    db.refresh(course)
    return _course_to_dict(course)


@router.delete("/cursos/{course_id}", status_code=204)
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.institution_id == inst_id,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    db.delete(course)
    db.commit()


# ─── MATERIAS ────────────────────────────────────────────────────────────────
@router.get("/materias")
def list_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    subjects = db.query(Subject).filter(Subject.institution_id == inst_id).all()
    return [{"id": s.id, "name": s.name, "baseType": s.base_type} for s in subjects]


@router.post("/materias", status_code=201)
async def create_subject(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    body = await request.json()
    name = (body.get("name") or "").strip()
    base_type = body.get("baseType") or body.get("base_type") or "matematicas"

    if not name:
        raise HTTPException(status_code=400, detail="El nombre es requerido")

    subject = Subject(name=name, base_type=base_type, institution_id=inst_id)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return {"id": subject.id, "name": subject.name, "baseType": subject.base_type}


# ─── SUPERVISIÓN ─────────────────────────────────────────────────────────────
@router.get("/supervision/estudiantes")
def supervision_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst_id = _check_institution(current_user)
    students = db.query(Student).filter(Student.institution_id == inst_id).all()
    return [_student_to_dict(s) for s in students]


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def _user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "fullName": u.full_name,
        "role": u.role.value,
        "subRole": u.sub_role.value if u.sub_role else None,
        "photoUrl": u.photo_url,
        "institutionId": u.institution_id,
        "courseId": u.course_id,
        "isActive": u.is_active,
        "createdAt": u.created_at.isoformat(),
        "updatedAt": u.updated_at.isoformat(),
    }


def _course_to_dict(c: Course) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "grade": c.grade,
        "group": c.group,
        "institutionId": c.institution_id,
        "teacherId": c.teacher_id,
        "createdAt": c.created_at.isoformat(),
    }


def _student_to_dict(s: Student) -> dict:
    return {
        "id": s.id,
        "fullName": s.full_name,
        "photoUrl": s.photo_url,
        "courseId": s.course_id,
        "institutionId": s.institution_id,
        "createdBy": s.created_by_id,
        "createdAt": s.created_at.isoformat(),
        "updatedAt": s.updated_at.isoformat(),
    }
