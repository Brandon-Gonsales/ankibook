from pathlib import Path
from typing import Any

import firebase_admin
from fastapi.concurrency import run_in_threadpool
from firebase_admin import auth, credentials

from app.core.config import settings


class FirebaseConfigurationError(RuntimeError):
    """Raised when Firebase Admin cannot be initialized safely."""


def get_firebase_app() -> firebase_admin.App:
    """Return the single Firebase Admin application, initializing it lazily."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    credential_path = settings.FIREBASE_CREDENTIALS_PATH
    if credential_path is None:
        raise FirebaseConfigurationError(
            "FIREBASE_CREDENTIALS_PATH is not configured"
        )

    path = Path(credential_path).expanduser()
    if not path.is_file():
        raise FirebaseConfigurationError(
            f"Firebase credentials file does not exist: {path}"
        )

    options: dict[str, str] | None = None
    if settings.FIREBASE_PROJECT_ID:
        options = {"projectId": settings.FIREBASE_PROJECT_ID}

    try:
        return firebase_admin.initialize_app(
            credentials.Certificate(str(path)),
            options=options,
        )
    except (OSError, ValueError) as exc:
        raise FirebaseConfigurationError(
            "Firebase Admin credentials could not be loaded"
        ) from exc


async def verify_firebase_id_token(id_token: str) -> dict[str, Any]:
    """Verify a client ID token without blocking FastAPI's event loop."""
    app = get_firebase_app()
    return await run_in_threadpool(auth.verify_id_token, id_token, app)
