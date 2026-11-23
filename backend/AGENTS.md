# AGENTS.md - AnkiBook Backend Architecture & Guidelines

Guía de arquitectura, convenciones y referencia del backend de **AnkiBook**, construido con **FastAPI**, **SQLModel**, **PostgreSQL (Supabase)** y autenticación mediante **Firebase Auth**.

---

## 1. Visión General del Proyecto

* **Propósito:** Backend REST API para la plataforma AnkiBook (creación de libros y lecciones de estudio con tarjetas mnemotécnicas, repetición espaciada y registro de repasos).
* **Framework Web:** [FastAPI](https://fastapi.tiangolo.com/) (asíncrono, OpenAPI nativo).
* **ORM / Modelado:** [SQLModel](https://sqlmodel.tiangolo.com/) (unión de Pydantic y SQLAlchemy 2.0).
* **Base de Datos:** PostgreSQL en [Supabase](https://supabase.com/) (esquema `public`).
* **Autenticación:** [Firebase Auth](https://firebase.google.com/docs/auth) en el frontend.
  * **Estrategia Minimalista (Opción 1 elegida):** La tabla `users.id` almacena directamente el `uid` (string) emitido por Firebase, eliminando duplicidades y evitando tablas o campos redundantes.
* **Driver de BD:** Soporte asíncrono para `asyncpg` (`postgresql+asyncpg://`) y `psycopg` (`postgresql+psycopg://`).

---

## 2. Estructura del Proyecto (Arquitectura en Capas)

```text
ankibook/
├── .venv/                         # Entorno virtual Python (3.14+)
├── .env                           # Variables de entorno locales
├── .env.example                   # Plantilla de variables de entorno
├── .gitignore                     # Exclusiones de Git
├── requirements.txt               # Dependencias del proyecto
├── AGENTS.md                      # Este documento de arquitectura
├── README.md                      # Documentación del proyecto
├── app/
│   ├── __init__.py
│   ├── main.py                    # Inicialización de FastAPI, lifespan, CORS y rutas
│   ├── core/                      # Configuración central
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic Settings (.env, DATABASE_URL dinámica)
│   │   └── database.py            # Motor AsyncEngine, AsyncSession, get_db y salud de BD
│   ├── models/                    # Modelos de base de datos (SQLModel)
│   │   ├── __init__.py            # Exportación unificada de modelos
│   │   ├── enums.py               # CardState y ReviewDirection
│   │   ├── user.py                # Modelo User (id = Firebase UID)
│   │   ├── ankibook.py            # Modelo Ankibook
│   │   ├── ankilection.py         # Modelo Ankilection
│   │   ├── ankicard.py            # Modelo AnkiCard
│   │   ├── user_card_progress.py  # Modelo UserCardProgress
│   │   └── review_log.py          # Modelo ReviewLog
│   ├── schemas/                   # Esquemas Pydantic (DTOs / Request / Response)
│   │   └── __init__.py
│   ├── repositories/              # Capa de acceso a datos (Queries / CRUD)
│   │   └── __init__.py
│   ├── services/                  # Lógica de negocio (Algoritmo SRS, etc.)
│   │   └── __init__.py
│   └── api/                       # Capa de controladores / endpoints HTTP
│       ├── __init__.py
│       ├── router.py              # Enrutador central v1
│       └── v1/
│           ├── __init__.py
│           └── endpoints/
│               ├── __init__.py
│               └── health.py      # Rutas /health y /api/v1/health
└── tests/                         # Suite de pruebas unitarias e integración
    ├── __init__.py
    ├── conftest.py                # Fixtures de Pytest (AsyncClient de httpx)
    ├── test_health.py             # Pruebas de rutas de salud
    └── test_models.py             # Pruebas de instanciación y reglas de modelos
```

---

## 3. Esquema de Base de Datos y Modelos SQLModel

Todos los modelos residen en el esquema `public`.

### 3.1. `users` ([user.py](file:///c:/Users/Usuario/Documents/svelpy/ankibook/app/models/user.py))
* `id` (`text`, PK): **Firebase UID** directamente (ej. `"pYj83Nf9Kl..."`). Es el único campo de la tabla (enfoque ultra-minimalista: todo perfil y correo residen únicamente en Firebase Auth).
* *Relaciones:* `ankibooks` (1:N), `card_progress` (1:N), `review_logs` (1:N).

### 3.2. `ankibooks` ([ankibook.py](file:///c:/Users/Usuario/Documents/svelpy/ankibook/app/models/ankibook.py))
* `id` (`uuid`, PK, DEFAULT `gen_random_uuid()`).
* `author_id` (`text`, FK `public.users.id`, ON DELETE CASCADE, INDEX).
* `title` (`text`, NOT NULL).
* `description` (`text`, NULL).
* `target_lang` (`text`, NOT NULL).
* `base_lang` (`text`, NOT NULL, DEFAULT `'es'`).
* `created_at` (`timestamptz`, NOT NULL, DEFAULT `CURRENT_TIMESTAMP`).
* *Check Constraint:* `CHECK (target_lang <> base_lang)`.
* *Relaciones:* `author` (N:1 con User), `ankilections` (1:N ordenado por `position`).

### 3.3. `ankilections` ([ankilection.py](file:///c:/Users/Usuario/Documents/svelpy/ankibook/app/models/ankilection.py))
* `id` (`uuid`, PK, DEFAULT `gen_random_uuid()`).
* `ankibook_id` (`uuid`, FK `public.ankibooks.id`, ON DELETE CASCADE, INDEX).
* `name` (`text`, NOT NULL).
* `position` (`int`, NOT NULL, DEFAULT `0`).
* *Índice:* `ankilections_idx_ankilections_ankibook_id`.
* *Relaciones:* `ankibook` (N:1), `ankicards` (1:N).

### 3.4. `ankicards` ([ankicard.py](file:///c:/Users/Usuario/Documents/svelpy/ankibook/app/models/ankicard.py))
* `id` (`uuid`, PK, DEFAULT `gen_random_uuid()`).
* `ankilection_id` (`uuid`, FK `public.ankilections.id`, ON DELETE CASCADE, INDEX).
* `base_text` (`text`, NOT NULL).
* `target_1` (`text`, NOT NULL).
* `target_2`, `target_3` (`text`, NULL).
* `reading` (`text`, NULL).
* `example_base` (`text`, NOT NULL).
* `example_target_1` (`text`, NOT NULL).
* `example_target_2`, `example_target_3` (`text`, NULL).
* `created_at` (`timestamptz`, NOT NULL, DEFAULT `CURRENT_TIMESTAMP`).
* *Índice:* `ankicards_idx_ankicards_ankilection_id`.
* *Check Constraints:*
  * `CHECK (target_2 IS NOT NULL OR target_3 IS NULL)`.
  * `CHECK (example_target_2 IS NOT NULL OR example_target_3 IS NULL)`.
* *Relaciones:* `ankilection` (N:1), `card_progress` (1:N), `review_logs` (1:N).

### 3.5. `user_card_progress` ([user_card_progress.py](file:///c:/Users/Usuario/Documents/svelpy/ankibook/app/models/user_card_progress.py))
* `id` (`uuid`, PK, DEFAULT `gen_random_uuid()`).
* `user_id` (`text`, FK `public.users.id`, ON DELETE CASCADE, INDEX).
* `ankicard_id` (`uuid`, FK `public.ankicards.id`, ON DELETE CASCADE, INDEX).
* `state` (`text`, NOT NULL, DEFAULT `'new'`).
* `due` (`timestamptz`, NOT NULL, DEFAULT `CURRENT_TIMESTAMP`).
* `interval_days` (`real`, NOT NULL, DEFAULT `0.0`).
* `ease` (`real`, NOT NULL, DEFAULT `2.5`).
* `reps` (`int`, NOT NULL, DEFAULT `0`).
* `lapses` (`int`, NOT NULL, DEFAULT `0`).
* `last_review` (`timestamptz`, NULL).
* *Índice:* `user_card_progress_idx_user_card_progress_user_id_due` en `(user_id, due)`.
* *Check Constraint:* `CHECK (state IN ('new', 'learning', 'review', 'relearning'))`.
* *Relaciones:* `user` (N:1), `ankicard` (N:1).

### 3.6. `review_log` ([review_log.py](file:///c:/Users/Usuario/Documents/svelpy/ankibook/app/models/review_log.py))
* `id` (`bigserial` / `BigInteger`, PK autoincrementable).
* `user_id` (`text`, FK `public.users.id`, ON DELETE CASCADE, INDEX).
* `ankicard_id` (`uuid`, FK `public.ankicards.id`, ON DELETE CASCADE, INDEX).
* `direction` (`text`, NOT NULL).
* `rating` (`smallint`, NOT NULL).
* `reviewed_at` (`timestamptz`, NOT NULL, DEFAULT `CURRENT_TIMESTAMP`).
* *Índice:* `review_log_idx_review_log_user_id_reviewed_at` en `(user_id, reviewed_at)`.
* *Check Constraints:*
  * `CHECK (direction IN ('base_to_target', 'target_to_base'))`.
  * `CHECK (rating BETWEEN 1 AND 4)`.
* *Relaciones:* `user` (N:1), `ankicard` (N:1).

---

## 4. Rutas y Endpoints Implementados

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/` | Información general, versión y enlaces a docs |
| `GET` | `/health` | Chequeo de salud del backend y estado de conexión con PostgreSQL |
| `GET` | `/api/v1/health` | Chequeo de salud bajo prefijo v1 |
| `GET` | `/docs` | Documentación interactiva Swagger UI |
| `GET` | `/redoc` | Documentación alternativa ReDoc |

### Ejemplo de respuesta de `/health`:
```json
{
  "status": "healthy",
  "app": "AnkiBook Backend API",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-10-19T21:28:00.000000Z",
  "database": {
    "status": "connected",
    "healthy": true
  }
}
```

---

## 5. Instrucciones de Ejecución

### 5.1. Activar el entorno virtual
En Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 5.2. Configurar Base de Datos (.env)
Añade la URL de Supabase o tu PostgreSQL local en `.env`:
```env
DATABASE_URL="postgresql+asyncpg://fidelity_user:fidelity_password@localhost:5432/fidelity_db"
```

### 5.3. Iniciar el Servidor de Desarrollo
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.4. Ejecutar la Suite de Pruebas
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 6. Próximas Fases de Desarrollo

1. **Fase 2 - Esquemas Pydantic (`app/schemas/`):**
   * Definición de esquemas de lectura y creación (`UserRead`, `AnkibookCreate`, `AnkibookRead`, `AnkilectionCreate`, `AnkiCardCreate`, `ReviewLogCreate`, etc.).
2. **Fase 3 - Middleware / Dependencia de Firebase Auth:**
   * Dependencia `get_current_user(token: str = Depends(oauth2_scheme))` para validar el Firebase ID Token y resolver/crear el `User` en base de datos.
3. **Fase 4 - Servicios y Algoritmo SRS (`app/services/`):**
   * Lógica de actualización de `ease`, `interval_days`, `reps` y `lapses` en base al `rating` (1 a 4) según el algoritmo de repetición espaciada.
4. **Fase 5 - Controladores CRUD (`app/api/v1/endpoints/`):**
   * Endpoints para creación de libros, lecciones en orden secuencial, tarjetas masivas y sesión de repaso interactiva.
