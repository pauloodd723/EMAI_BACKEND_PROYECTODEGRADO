from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .database import engine, SessionLocal
from .models import Base, User, UserRoleEnum
from .security import hash_password
from .routers import auth, admin, directivo, docente, soporte


def _seed_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == UserRoleEnum.admin).first():
            db.add(User(
                username="admin",
                password_hash=hash_password("Admin1234!"),
                full_name="Administrador EMAI",
                role=UserRoleEnum.admin,
                is_active=True,
            ))
            db.commit()
            print("✓ Usuario admin creado (admin / Admin1234!)")
    except Exception as e:
        print(f"⚠ Seed admin: {e}")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        _seed_admin()
    except Exception as e:
        print(f"⚠ BD: {e}")
    # Pre-cargar EasyOCR en background para que el primer escaneo no espere
    import threading
    def _warmup_ocr():
        try:
            from .services.ocr_service import _get_easyocr
            _get_easyocr()
            print("✓ EasyOCR modelo cargado y listo")
        except Exception as e:
            print(f"⚠ EasyOCR warmup: {e}")
    threading.Thread(target=_warmup_ocr, daemon=True).start()
    print(f"✓ {settings.APP_NAME} v{settings.APP_VERSION} iniciado")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API para EMAI-APP",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(auth.router,      prefix=PREFIX)
app.include_router(admin.router,     prefix=PREFIX)
app.include_router(directivo.router, prefix=PREFIX)
app.include_router(docente.router,   prefix=PREFIX)
app.include_router(soporte.router,   prefix=PREFIX)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
