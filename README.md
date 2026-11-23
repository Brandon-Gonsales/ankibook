# AnkiBook

Aplicación de estudio con libros, lecciones y tarjetas de repetición espaciada.

| Carpeta | Qué contiene |
| --- | --- |
| [`backend/`](backend/) | API REST con FastAPI + SQLModel + PostgreSQL, autenticación con Firebase Admin |
| [`frontend/`](frontend/) | SPA móvil con SvelteKit + Firebase Auth (Google) |

## Requisitos

- Python 3.14+
- Node.js 20+
- PostgreSQL
- Un proyecto de Firebase (credenciales web para el frontend y una cuenta de servicio para el backend)

## Puesta en marcha local

### 1. Backend

> Ejecuta **todos** los comandos del backend desde la carpeta `backend/`: la configuración lee el `.env` del directorio actual.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env        # completa DATABASE_URL y las credenciales de Firebase
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

La API queda en `http://localhost:8000` (documentación en `/docs`).

Pruebas:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### 2. Frontend

```powershell
cd frontend
npm install
copy .env.example .env        # completa las claves VITE_FIREBASE_*
npm run dev                   # http://localhost:5173
```

En desarrollo, Vite reenvía `/api` al backend en `localhost:8000`. Más detalles en [`frontend/README.md`](frontend/README.md).

## Seguridad

- **Nunca subas** archivos `.env` ni el JSON de la cuenta de servicio de Firebase. Usa los `.env.example` como plantilla.
- `ENVIRONMENT="development"` activa un atajo de login sin Firebase: úsalo solo en local. En el servidor debe ser `ENVIRONMENT="production"`.
