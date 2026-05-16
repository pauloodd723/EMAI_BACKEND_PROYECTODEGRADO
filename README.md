# EMAI-APP — Backend

API REST en Python + FastAPI para el sistema de seguimiento de exámenes.

## Stack
- **FastAPI** — framework web async
- **SQLAlchemy 2.0** — ORM
- **MySQL / MariaDB** — base de datos (via MySQL Workbench)
- **pytesseract + Pillow** — OCR de exámenes
- **python-jose** — JWT
- **passlib[bcrypt]** — hashing de contraseñas

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Instalar Tesseract OCR en el sistema
# macOS:
brew install tesseract tesseract-lang
# Ubuntu/Debian:
sudo apt install tesseract-ocr tesseract-ocr-spa
# Windows: descargar instalador de https://github.com/UB-Mannheim/tesseract/wiki

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración de MySQL

# 5. Crear base de datos en MySQL Workbench
# CREATE DATABASE emai_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 6. Seed: crear primer admin
python -m scripts.seed_admin

# 7. Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Estructura

```
emai-backend/
├── app/
│   ├── main.py           # FastAPI app, CORS, routers
│   ├── config.py         # Settings con pydantic
│   ├── database.py       # SQLAlchemy engine + sesión
│   ├── models.py         # Tablas: Institution, User, Course...
│   ├── schemas.py        # Pydantic schemas (request/response)
│   ├── security.py       # JWT, bcrypt, dependencias auth
│   ├── routers/
│   │   ├── auth.py       # /auth/login, /auth/redeem-token...
│   │   ├── admin.py      # /admin/tokens, /admin/admins...
│   │   ├── directivo.py  # /directivo/usuarios, /directivo/cursos...
│   │   ├── docente.py    # /docente/examenes, /docente/escanear...
│   │   └── soporte.py    # /soporte (compartido)
│   └── services/
│       └── ocr_service.py # OCR + detección de problemas matemáticos
└── scripts/
    └── seed_admin.py     # Crea el primer admin
```

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Iniciar sesión |
| POST | `/api/v1/auth/redeem-token` | Validar token de institución |
| POST | `/api/v1/auth/create-account` | Crear cuenta directivo con token |
| PATCH | `/api/v1/auth/perfil` | Actualizar perfil |
| GET | `/api/v1/admin/stats` | Stats del admin |
| POST | `/api/v1/admin/tokens` | Generar token de institución |
| GET | `/api/v1/admin/tokens` | Listar tokens |
| POST | `/api/v1/admin/admins` | Crear administrador |
| GET | `/api/v1/admin/soporte` | Bandeja de soporte |
| GET | `/api/v1/directivo/stats` | Stats del directivo |
| POST | `/api/v1/directivo/usuarios` | Crear docente/directivo |
| GET | `/api/v1/directivo/cursos` | Listar cursos |
| POST | `/api/v1/directivo/cursos` | Crear curso |
| GET | `/api/v1/docente/stats` | Stats del docente |
| GET | `/api/v1/docente/cursos` | Cursos del docente |
| POST | `/api/v1/docente/estudiantes` | Crear estudiante |
| POST | `/api/v1/docente/examenes` | Crear examen |
| POST | `/api/v1/docente/examenes/escanear` | **OCR + calificación automática** |
| GET | `/api/v1/docente/examenes/resultados/{id}` | Ver resultado con problemas |
| PATCH | `/api/v1/docente/examenes/resultados/{id}` | Guardar correcciones manuales |
| GET | `/api/v1/docente/reportes` | Estadísticas y gráficas |

## OCR — cómo funciona

1. El frontend envía 1–3 imágenes en **base64**
2. El backend las decodifica y aplica preprocesamiento (escala de grises, contraste, nitidez)
3. **Tesseract** extrae el texto en español
4. Se aplican **14 patrones regex** para detectar ecuaciones y problemas matemáticos
5. Para operaciones básicas (`5 + 3 = 8`) se verifica automáticamente la respuesta
6. Se calcula la nota final en escala colombiana **(1.0 – 5.0)**
7. El proceso corre en **background** para no bloquear la respuesta

## Conectar con el celular (Expo Go)

1. El celular y el PC deben estar en la **misma red WiFi**
2. Obtén la IP de tu PC: `ipconfig` (Windows) o `ifconfig` (macOS/Linux)
3. En el frontend (`src/constants/index.ts`): `API_BASE_URL = 'http://192.168.X.X:8000/api/v1'`
4. En `.env`: agrega la IP del celular a `ALLOWED_ORIGINS`
5. Inicia el servidor con `--host 0.0.0.0`

## Documentación interactiva

Con `DEBUG=True`, disponible en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
