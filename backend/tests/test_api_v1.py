import pytest
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.api.v1.endpoints import ankibooks, reviews
from app.core.database import get_db
from app.main import app
from app.models import Ankibook, User
from app.schemas import AnkibookRead


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/ankibooks",
        "/api/v1/ankibooks/explore",
        "/api/v1/auth/me",
        "/api/v1/reviews/due",
        "/api/v1/reviews/summary",
    ],
)
async def test_protected_routes_require_authentication(
    client: AsyncClient,
    path: str,
) -> None:
    response = await client.get(path)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_ankibook_uses_authenticated_user(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()

    async def override_user() -> User:
        return User(id="firebase-uid")

    async def override_db():
        yield session

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(ankibooks, "AnkibookRepository", FakeAnkibookRepository)
    try:
        response = await client.post(
            "/api/v1/ankibooks",
            json={"title": "English", "target_lang": "en"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["author_id"] == "firebase-uid"
    assert response.json()["base_lang"] == "es"
    assert response.json()["is_owner"] is True
    assert session.committed is True


@pytest.mark.asyncio
async def test_due_cards_endpoint_delegates_to_review_service(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def override_user() -> User:
        return User(id="firebase-uid")

    async def override_db():
        yield FakeSession()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(reviews, "ReviewService", FakeReviewService)
    try:
        response = await client.get(
            "/api/v1/reviews/due?limit=10&lection_id=3f1c2a8e-1b2c-4d5e-8f90-123456789abc"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


def test_openapi_contains_crud_and_review_routes() -> None:
    paths = app.openapi()["paths"]

    assert set(paths["/api/v1/ankibooks"]) >= {"get", "post"}
    assert set(paths["/api/v1/ankibooks/{book_id}"]) >= {
        "get",
        "patch",
        "delete",
    }
    assert set(paths["/api/v1/lections/{lection_id}/cards"]) >= {"get", "post"}
    assert set(paths["/api/v1/reviews"]) >= {"post"}
    assert set(paths["/api/v1/reviews/summary"]) >= {"get"}
    assert set(paths["/api/v1/reviews/{card_id}/bury"]) >= {"post"}
    assert set(paths["/api/v1/auth/me"]) >= {"get"}
    assert set(paths["/api/v1/ankibooks/explore"]) >= {"get"}
    assert set(paths["/api/v1/ankibooks/{book_id}/library"]) >= {"put", "delete"}


BOOK_ID = "3f1c2a8e-1b2c-4d5e-8f90-123456789abc"


class FakeLibraryRepository:
    """Book exists unless flagged missing; owned when the caller is "author"."""

    added: list[tuple[str, str]] = []
    missing = False

    def __init__(self, session) -> None:
        self.session = session

    async def exists(self, book_id) -> bool:
        return not self.missing

    async def get_owned(self, user_id, book_id):
        return object() if user_id == "author" else None

    async def add_to_library(self, user_id, book_id) -> None:
        self.added.append((user_id, str(book_id)))


async def _put_library(client, monkeypatch, uid: str, missing: bool = False):
    session = FakeSession()

    async def override_user() -> User:
        return User(id=uid)

    async def override_db():
        yield session

    FakeLibraryRepository.added = []
    FakeLibraryRepository.missing = missing
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(ankibooks, "AnkibookRepository", FakeLibraryRepository)
    try:
        return await client.put(f"/api/v1/ankibooks/{BOOK_ID}/library"), session
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_add_foreign_book_to_library(client, monkeypatch) -> None:
    response, session = await _put_library(client, monkeypatch, "reader")

    assert response.status_code == 204
    assert FakeLibraryRepository.added == [("reader", BOOK_ID)]
    assert session.committed is True


@pytest.mark.asyncio
async def test_adding_own_book_is_a_no_op(client, monkeypatch) -> None:
    response, session = await _put_library(client, monkeypatch, "author")

    assert response.status_code == 204
    assert FakeLibraryRepository.added == []
    assert session.committed is False


@pytest.mark.asyncio
async def test_adding_missing_book_returns_404(client, monkeypatch) -> None:
    response, _ = await _put_library(client, monkeypatch, "reader", missing=True)

    assert response.status_code == 404
    assert FakeLibraryRepository.added == []


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeAnkibookRepository:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def create(self, user_id, data) -> Ankibook:
        return Ankibook(author_id=user_id, **data.model_dump())

    async def list_for_user(self, user_id) -> list[AnkibookRead]:
        return []


class FakeReviewService:
    def __init__(self, repository) -> None:
        self.repository = repository

    async def get_due_cards(
        self, user_id, *, due_at=None, limit=20, book_id=None, lection_id=None, extra_new=0
    ):
        assert user_id == "firebase-uid"
        assert limit == 10
        assert str(lection_id) == "3f1c2a8e-1b2c-4d5e-8f90-123456789abc"
        assert book_id is None
        return []
