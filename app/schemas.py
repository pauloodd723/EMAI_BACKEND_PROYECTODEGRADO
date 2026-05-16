from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ─── ENUMS ────────────────────────────────────────────────────────────────────
class UserRole(str, Enum):
    admin = "admin"
    directivo = "directivo"
    docente = "docente"


class DirectivoSubRole(str, Enum):
    director = "director"
    subdirector = "subdirector"
    coordinador = "coordinador"
    psicologo = "psicologo"
    otro = "otro"


class ExamStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    reviewed = "reviewed"
    graded = "graded"


# ─── AUTH ─────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class RedeemTokenRequest(BaseModel):
    token: str


class CreateAccountRequest(BaseModel):
    username: str = Field(min_length=4, max_length=80)
    password: str = Field(min_length=6)
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    photo_url: Optional[str] = None


# ─── INSTITUCIÓN ──────────────────────────────────────────────────────────────
class InstitutionOut(BaseModel):
    id: str
    name: str
    primary_color: str
    secondary_color: str
    logo_url: Optional[str]
    data_terms_accepted: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UpdateInstitutionRequest(BaseModel):
    name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None


# ─── USUARIO ──────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id: str
    username: str
    full_name: str
    role: UserRole
    sub_role: Optional[DirectivoSubRole]
    photo_url: Optional[str]
    institution_id: Optional[str]
    course_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=4, max_length=80)
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2)
    role: UserRole
    sub_role: Optional[DirectivoSubRole] = None
    course_id: Optional[str] = None


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    sub_role: Optional[DirectivoSubRole] = None
    course_id: Optional[str] = None
    photo_url: Optional[str] = None


# ─── LOGIN RESPONSE ───────────────────────────────────────────────────────────
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    institution: Optional[InstitutionOut]


# ─── TOKEN DE INSTITUCIÓN ─────────────────────────────────────────────────────
class AccessTokenOut(BaseModel):
    id: str
    token: str
    institution_name: Optional[str]
    used: bool
    used_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class CreateAccessTokenRequest(BaseModel):
    institution_name: Optional[str] = None


# ─── CURSO ────────────────────────────────────────────────────────────────────
class CourseOut(BaseModel):
    id: str
    name: str
    grade: str
    group: str
    institution_id: str
    teacher_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CreateCourseRequest(BaseModel):
    grade: str
    group: str
    name: str


# ─── MATERIA ──────────────────────────────────────────────────────────────────
class SubjectOut(BaseModel):
    id: str
    name: str
    base_type: str
    institution_id: str

    class Config:
        from_attributes = True


class CreateSubjectRequest(BaseModel):
    name: str
    base_type: str = "matematicas"


# ─── ESTUDIANTE ───────────────────────────────────────────────────────────────
class StudentOut(BaseModel):
    id: str
    full_name: str
    photo_url: Optional[str]
    course_id: str
    institution_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CreateStudentRequest(BaseModel):
    full_name: str = Field(min_length=2)
    course_id: str
    photo_url: Optional[str] = None


class UpdateStudentRequest(BaseModel):
    full_name: Optional[str] = None
    photo_url: Optional[str] = None


# ─── EXAMEN ───────────────────────────────────────────────────────────────────
class ExamOut(BaseModel):
    id: str
    name: str
    course_id: str
    subject_id: Optional[str]
    teacher_id: str
    institution_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class CreateExamRequest(BaseModel):
    name: str = Field(min_length=5)
    course_id: str
    subject_id: Optional[str] = None


# ─── PROBLEMA MATEMÁTICO ──────────────────────────────────────────────────────
class ExamProblem(BaseModel):
    id: str
    original_text: str
    is_correct: bool
    auto_score: float
    teacher_override: bool = False
    teacher_score: Optional[float] = None


# ─── RESULTADO DE EXAMEN ──────────────────────────────────────────────────────
class ExamResultOut(BaseModel):
    id: str
    exam_id: str
    student_id: str
    image_urls: List[str]
    ocr_raw_text: Optional[str]
    problems: Optional[List[ExamProblem]]
    final_score: Optional[float]
    grade_color: Optional[str]
    teacher_notes: Optional[str]
    status: ExamStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScanExamRequest(BaseModel):
    student_id: str
    exam_id: Optional[str] = None
    course_id: Optional[str] = None
    images: List[str]          # base64
    image_count: int


class UpdateExamResultRequest(BaseModel):
    problems: Optional[List[ExamProblem]] = None
    teacher_notes: Optional[str] = None
    final_score: Optional[float] = None


# ─── SOPORTE ──────────────────────────────────────────────────────────────────
class SupportMessageOut(BaseModel):
    id: str
    from_user_id: str
    from_username: str
    from_role: str
    institution_id: Optional[str]
    message: str
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreateSupportMessageRequest(BaseModel):
    message: str = Field(min_length=10, max_length=1000)


# ─── STATS ────────────────────────────────────────────────────────────────────
class AdminStats(BaseModel):
    total_tokens: int
    tokens_usados: int
    total_instituciones: int
    total_admins: int
    mensajes_sin_leer: int


class DirectivoStats(BaseModel):
    total_directivos: int
    total_docentes: int
    total_cursos: int
    total_estudiantes: int


class DocenteStats(BaseModel):
    total_estudiantes: int
    total_examenes: int
    examenes_hoy: int
    promedio_general: Optional[float]


class ReportData(BaseModel):
    total_examenes: int
    total_estudiantes: int
    aprobados: int
    reprobados: int
    promedio_general: float
    promedios_por_curso: list
    distribucion: list
