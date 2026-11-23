from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import exceptions as firebase_exceptions
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.firebase import FirebaseConfigurationError, verify_firebase_id_token
from app.models.user import User
from app.repositories.user import UserRepository


security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    auth_header: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(security_scheme),
    ],
    x_user_id: Annotated[
        Optional[str],
        Header(description="Direct Firebase UID for local development only"),
    ] = None,
    session: Annotated[AsyncSession, Depends(get_db)] = None,
) -> User:
    """Verify a Firebase ID Token and provision its UID in PostgreSQL."""
    uid: Optional[str] = None

    if auth_header and auth_header.credentials:
        try:
            decoded_token = await verify_firebase_id_token(
                auth_header.credentials.strip()
            )
            uid = decoded_token.get("uid")
        except FirebaseConfigurationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Firebase Authentication no está configurado en el servidor.",
            ) from exc
        except (ValueError, firebase_exceptions.FirebaseError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El token de Firebase es inválido o expiró.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
    elif x_user_id and settings.is_development:
        uid = x_user_id.strip()

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un ID Token válido de Firebase.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repository = UserRepository(session)
    try:
        user = await repository.get_or_create(uid)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return user
