# EMAI-APP — Backend

API REST en Python + FastAPI para el sistema de seguimiento de exámenes.

## Stack
- **FastAPI** — framework web async
- **SQLAlchemy 2.0** — ORM
- **MySQL / MariaDB** — base de datos (via MySQL Workbench)
- **pytesseract + Pillow** — OCR de exámenes
- **python-jose** — JWT
- **passlib[bcrypt]** — hashing de contraseñas

---

## Instalación

### 1. Clonar e instalar dependencias

```bash

# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Instalar Tesseract OCR en el sistema

```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt install tesseract-ocr tesseract-ocr-spa

# Windows
# Descargar instalador de: https://github.com/UB-Mannheim/tesseract/wiki
# Durante la instalación marcar el idioma "Spanish"
# Agregar al PATH del sistema: C:\Program Files\Tesseract-OCR
# Verificar con: tesseract --version
```

---

## Configurar la base de datos local (MySQL Workbench)

### Paso 1 — Instalar MySQL

Descarga e instala **MySQL Community Server** desde https://dev.mysql.com/downloads/mysql/  
Durante la instalación configura una contraseña para el usuario `root`.

### Paso 2 — Crear la base de datos

Abre **MySQL Workbench**, conéctate a tu instancia local y ejecuta:

```sql
CREATE DATABASE emai_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Verifica que se creó:

```sql
SHOW DATABASES;
-- Debe aparecer: emai_db
```

### Paso 3 — Configurar las variables de entorno

Copia el archivo de ejemplo y edítalo:

```bash
cp .env.example .env
```

Abre `.env` y completa estos campos:

```env
# Base de datos
DATABASE_URL=mysql+pymysql://root:TU_CONTRASEÑA@localhost:3306/emai_db

# JWT — genera una clave segura con: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=pega_aqui_tu_clave_generada
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# OCR
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe   # Windows
# TESSERACT_CMD=/usr/bin/tesseract                            # Linux/macOS
OCR_LANG=spa+eng

# App
DEBUG=True
ALLOWED_ORIGINS=http://localhost:8081,http://localhost:19006,exp://192.168.1.X:8081
```

> **Nota:** reemplaza `TU_CONTRASEÑA` con la que pusiste al instalar MySQL, y `192.168.1.X` con la IP real de tu celular en la red WiFi.

### Paso 4 — Crear las tablas e insertar el primer admin

```bash
# Crea todas las tablas en emai_db automáticamente
python -m scripts.seed_admin
```

Si todo está bien verás:
```
✅ Tablas creadas
✅ Admin creado: admin / admin123
```

---

## Iniciar el servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El servidor quedará escuchando en `http://localhost:8000`.

---

## Exponer el backend al celular con ngrok

Expo Go en el celular no puede conectarse directamente a `localhost` de tu PC. Para eso se usa **ngrok**, que crea un túnel público.

### Paso 1 — Instalar ngrok

Descarga desde https://ngrok.com/download e instálalo.  
Crea una cuenta gratuita en ngrok.com y obtén tu **authtoken**.

Configura el authtoken una sola vez:

```bash
ngrok config add-authtoken TU_AUTHTOKEN_AQUI
```

### Paso 2 — Abrir el túnel (cada vez que trabajes)

Con el backend corriendo en el puerto 8000, abre una **terminal separada** y ejecuta:

```bash
ngrok http 8000
```

Verás algo como:

```
Forwarding   https://abc123-tu-url.ngrok-free.app -> http://localhost:8000
```

Copia esa URL `https://...ngrok-free.app`.

### Paso 3 — Configurar la URL en el frontend

Abre el archivo `src/constants/index.ts` en el proyecto de Expo y actualiza:

```typescript
export const API_BASE_URL = 'https://abc123-tu-url.ngrok-free.app/api/v1';
```

> **Importante:** ngrok genera una URL nueva cada vez que lo reinicias (en el plan gratuito). Debes actualizar `API_BASE_URL` cada sesión de trabajo.

### Paso 4 — Agregar la URL de ngrok a CORS

En `.env` agrega la URL de ngrok a `ALLOWED_ORIGINS`:

```env
ALLOWED_ORIGINS=http://localhost:8081,https://abc123-tu-url.ngrok-free.app
```

Reinicia el backend para que tome el cambio.

---

## Arranque diario (resumen)

Cada vez que vayas a trabajar abre **3 terminales**:

```powershell
# Terminal 1 — Backend
cd emai-app-backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — ngrok (nueva URL cada sesión)
ngrok http 8000
# Copiar la URL https://... y pegarla en src/constants/index.ts

# Terminal 3 — Expo
cd emai-app-sdk54
npx expo start --tunnel --clear
```

---

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

---

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
| GET | `/api/v1/docente/cursos/{id}/exportar-xlsx` | Exportar notas en Excel |
| GET | `/api/v1/docente/reportes` | Estadísticas y gráficas |

---

## OCR — cómo funciona

1. El frontend envía 1–3 imágenes en **base64**
2. El backend las decodifica y aplica preprocesamiento (brillo → threshold → escala de grises)
3. **Tesseract** extrae el texto en español + inglés (`spa+eng`)
4. El parser usa el signo `=` como **ancla principal** para detectar problemas matemáticos
5. Soporta: suma, resta, multiplicación, división, fracciones, decimales, jerarquía de operaciones, potencias, raíces, desigualdades V/F y unidades de medida
6. Se calcula la nota final en escala colombiana **(1.0 – 5.0)**
7. Se genera un **plan pedagógico automático** por tipo de error
8. El proceso corre en **background** para no bloquear la respuesta

---

## Credenciales de prueba

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin` | `admin123` | Administrador |
| `directivo_demo` | `director123` | Directivo |
| `docente_demo` | `docente123` | Docente |

Token de institución de prueba: `EMAI-TEST-0001`

---

## Documentación interactiva

Con `DEBUG=True`, disponible en:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
