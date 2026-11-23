from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import pytest

from app.api import deps
from app.core.firebase import FirebaseConfigurationError, get_firebase_app
from app.models import User


@pytest.mark.asyncio
async def test_firebase_token_uid_is_provisioned(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_verify(token: str):
        assert token == "valid-token"
        return {"uid": "firebase-uid", "email": "user@example.com"}

    monkeypatch.setattr(deps, "verify_firebase_id_token", fake_verify)
    monkeypatch.setattr(deps, "UserRepository", FakeUserRepository)
    session = FakeSession()

    user = await deps.get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token"),
        None,
        session,
    )

    assert user.id == "firebase-uid"
    assert session.committed is True


@pytest.mark.asyncio
async def test_invalid_firebase_token_returns_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_verify(token: str):
        raise ValueError("invalid token")

    monkeypatch.setattr(deps, "verify_firebase_id_token", fake_verify)

    with pytest.raises(HTTPException) as error:
        await deps.get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid"),
            None,
            FakeSession(),
        )

    assert error.value.status_code == 401


@pytest.mark.asyncio
async def test_development_header_is_disabled_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(deps.settings, "ENVIRONMENT", "production")

    with pytest.raises(HTTPException) as error:
        await deps.get_current_user(None, "untrusted-uid", FakeSession())

    assert error.value.status_code == 401


def test_missing_firebase_path_has_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(deps.settings, "FIREBASE_CREDENTIALS_PATH", None)

    with pytest.raises(FirebaseConfigurationError, match="not configured"):
        get_firebase_app()


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeUserRepository:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def get_or_create(self, user_id: str) -> User:
        return User(id=user_id)
