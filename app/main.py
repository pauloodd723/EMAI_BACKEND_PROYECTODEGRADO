from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .database import engine
from .models import Base
from .routers import auth, admin, directivo, docente, soporte


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"⚠ BD: {e}")
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
