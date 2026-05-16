import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Float,
    ForeignKey, Text, Integer, Enum as SAEnum
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.dialects.mysql import CHAR
import enum


def new_uuid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


# ─── ENUMS ────────────────────────────────────────────────────────────────────
class UserRoleEnum(str, enum.Enum):
    admin = "admin"
    directivo = "directivo"
    docente = "docente"


class DirectivoSubRoleEnum(str, enum.Enum):
    director = "director"
    subdirector = "subdirector"
    coordinador = "coordinador"
    psicologo = "psicologo"
    otro = "otro"


class ExamStatusEnum(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    reviewed = "reviewed"
    graded = "graded"


# ─── INSTITUCIÓN ──────────────────────────────────────────────────────────────
class Institution(Base):
    __tablename__ = "institutions"

    id = Column(CHAR(36), primary_key=True, default=new_uuid)
    name = Column(String(200), nullable=False)
    primary_color = Column(String(7), default="#1A3C5E")
    secondary_color = Column(String(7), default="#2E6DA4")
    logo_url = Column(String(500), nullable=True)
    data_terms_accepted = Column(Boolean, default=False)
    data_terms_accepted_at = Column(DateTime, nullable=True)
    data_terms_accepted_by = Column(CHAR(36), nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    # Relaciones
    users = relationship("User", back_populates="institution")
    tokens = relationship("AccessToken", back_populates="institution")
    courses = relationship("Course", back_populates="institution")
    subjects = relationship("Subject", back_populates="institution")
    students = relationship("Student", back_populates="institution")
    exams = relationship("Exam", back_populates="institution")
    support_messages = relationship("SupportMessage", back_populates="institution")


# ─── TOKEN DE ACCESO ──────────────────────────────────────────────────────────
class AccessToken(Base):
    __tablename__ = "access_tokens"

    id = Column(CHAR(36), primary_key=True, default=new_uuid)
    token = Column(String(30), unique=True, nullable=False, index=True)
    institution_name = Column(String(200), nullable=True)
    institution_id = Column(CHAR(36), ForeignKey("institutions.id"), nullable=True)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    used_by = Column(CHAR(36), nullable=True)
    created_by = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now)

    institution = relationship("Institution", back_populates="tokens")
    creator = relationship("User", foreign_keys=[created_by])


# ─── USUARIO ──────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=new_uuid)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(SAEnum(UserRoleEnum), nullable=False)
    sub_role = Column(SAEnum(DirectivoSubRoleEnum), nullable=True)
    photo_url = Column(String(500), nullable=True)
    institution_id = Column(CHAR(36), ForeignKey("institutions.id"), nullable=True)
    course_id = Column(CHAR(36), ForeignKey("courses.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    institution = relationship("Institution", back_populates="users")
    course = relationship("Course", foreign_keys=[course_id])
    created_students = relationship("Student", back_populates="created_by_user")
    created_exams = relationship("Exam", back_populates="teacher")


# ─── CURSO ────────────────────────────────────────────────────────────────────
class Course(Base):
    __tablename__ = "courses"

    id = Column(CHAR(36), primary_key=True, default=new_uuid)
    name = Column(String(20), nullable=False)
    grade = Column(String(10), nullable=False)
    group = Column(String(10), nullable=False)
    institution_id = Column(CHAR(36), ForeignKey("institutions.id"), nullable=False)
    teacher_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now)

    institution = relationship("Institution", back_populates="courses")
    teacher = relationship("User", foreign_keys=[teacher_id])
    students = relationship("Student", back_populates="course")
    exams = relationship("Exam", back_populates="course")


# ─── MATERIA ──────────────────────────────────────────────────────────────────
class Subject(Base):
    __tablename__ = "subjects"

    id = Column(CHAR(36), primary_key=True, default=new_uuid)
    name = Column(String(100), nullable=False)
    base_type = Column(String(30), default="matematicas")
    institution_id = Column(CHAR(36), ForeignKey("institutions.id"), nullable=False)
    course_id = Column(CHAR(36), nullable=True)
    created_at = Column(DateTime, default=now)

    institution = relationship("Institution", back_populates="subjects")
    exams = relationship("Exam", back_populates="subject")


# ─── ESTUDIANTE ───────────────────────────────────────────────────────────────
class Student(Base):
    __tablename__ = "students"

    id = Column(CHAR(36), primary_key=True, default=new_uuid)
    full_name = Column(String(200), nullable=False)
    photo_url = Column(String(500), nullable=True)
    course_id = Column(CHAR(36), ForeignKey("courses.id"), nullable=False)
    institution_id = Column(CHAR(36), ForeignKey("institutions.id"), nullable=False)
    created_by_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    course = relationship("Course", back_populates="students")
    institution = relationship("Institution", back_populates="students")
    created_by_user = relationship("User", back_populates="created_students")
    exam_results = relationship("ExamResult", back_populates="student")


# ─── EXAMEN ───────────────────────────────────────────────────────────────────
class Exam(Base):
    __tablename__ = "exams"

    id = Column(CHAR(36), primary_key=True, default=new_uuid)
    name = Column(String(300), nullable=False)
    course_id = Column(CHAR(36), ForeignKey("courses.id"), nullable=False)
    subject_id = Column(CHAR(36), ForeignKey("subjects.id"), nullable=True)
    teacher_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    institution_id = Column(CHAR(36), ForeignKey("institutions.id"), nullable=False)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    course = relationship("Course", back_populates="exams")
    subject = relationship("Subject", back_populates="exams")
    teacher = relationship("User", back_populates="created_exams")
    institution = relationship("Institution", back_populates="exams")
    results = relationship("ExamResult", back_populates="exam")


# ─── RESULTADO DE EXAMEN ──────────────────────────────────────────────────────
class ExamResult(Base):
    __tablename__ = "exam_results"

    id = Column(CHAR(36), primary_key=True, default=new_uuid)
    exam_id = Column(CHAR(36), ForeignKey("exams.id"), nullable=False)
    student_id = Column(CHAR(36), ForeignKey("students.id"), nullable=False)
    image_urls = Column(Text, nullable=True)          # JSON lista de URLs
    ocr_raw_text = Column(Text, nullable=True)
    problems_json = Column(Text, nullable=True)        # JSON lista de problemas
    final_score = Column(Float, nullable=True)
    grade_color = Column(String(10), nullable=True)    # "green" | "red"
    teacher_notes = Column(Text, nullable=True)
    status = Column(SAEnum(ExamStatusEnum), default=ExamStatusEnum.pending)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    exam = relationship("Exam", back_populates="results")
    student = relationship("Student", back_populates="exam_results")


# ─── MENSAJE DE SOPORTE ───────────────────────────────────────────────────────
class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(CHAR(36), primary_key=True, default=new_uuid)
    from_user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False)
    from_username = Column(String(80), nullable=False)
    from_role = Column(String(20), nullable=False)
    institution_id = Column(CHAR(36), ForeignKey("institutions.id"), nullable=True)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

    institution = relationship("Institution", back_populates="support_messages")
    sender = relationship("User", foreign_keys=[from_user_id])
