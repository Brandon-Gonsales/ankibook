import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.enums import CardState, ReviewDirection
from app.schemas import (
    AnkiCardBulkCreate,
    AnkiCardCreate,
    AnkiCardUpdate,
    AnkibookCreate,
    ReviewLogCreate,
    ReviewSubmission,
    UserCardProgressRead,
)


def test_card_create_allows_omitted_examples() -> None:
    card = AnkiCardCreate(base_text="hola", target_1="hello")

    assert card.example_base is None
    assert card.example_target_1 is None


def test_card_create_enforces_translation_order() -> None:
    with pytest.raises(ValidationError):
        AnkiCardCreate(base_text="hola", target_1="hello", target_3="hey")

    with pytest.raises(ValidationError):
        AnkiCardCreate(
            base_text="hola",
            target_1="hello",
            example_target_3="Hi there",
        )


def test_card_update_supports_partial_payloads() -> None:
    update = AnkiCardUpdate(target_3="hey")

    assert update.model_dump(exclude_unset=True) == {"target_3": "hey"}


def test_card_bulk_create_requires_at_least_one_card() -> None:
    with pytest.raises(ValidationError):
        AnkiCardBulkCreate(cards=[])


def test_book_languages_must_differ() -> None:
    with pytest.raises(ValidationError):
        AnkibookCreate(title="English", target_lang="EN", base_lang="en")


def test_schemas_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        AnkiCardCreate(base_text="hola", target_1="hello", unexpected=True)


def test_review_submission_reuses_review_create_schema() -> None:
    assert ReviewSubmission is ReviewLogCreate

    submission = ReviewSubmission(
        ankicard_id=uuid.uuid4(),
        direction=ReviewDirection.TARGET_TO_BASE,
        rating=4,
    )
    assert submission.rating == 4

    with pytest.raises(ValidationError):
        ReviewSubmission(ankicard_id=uuid.uuid4(), rating=5)


def test_progress_read_uses_card_state_enum() -> None:
    progress = UserCardProgressRead(
        id=uuid.uuid4(),
        user_id="firebase-user",
        ankicard_id=uuid.uuid4(),
        state="review",
        due=datetime.now(timezone.utc),
        interval_days=3,
        ease=2.5,
        reps=2,
        lapses=0,
    )

    assert progress.state is CardState.REVIEW


# --- Hardening: explicit nulls and size limits -------------------------------

from app.core.config import Settings  # noqa: E402
from app.schemas import AnkibookUpdate, AnkilectionCreate, AnkilectionUpdate  # noqa: E402
from app.schemas.limits import BULK_CARDS_MAX, CARD_TEXT_MAX, POSITION_MAX  # noqa: E402


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (AnkibookUpdate, {"title": None}),
        (AnkibookUpdate, {"target_lang": None}),
        (AnkilectionUpdate, {"name": None}),
        (AnkilectionUpdate, {"position": None}),
        (AnkiCardUpdate, {"base_text": None}),
        (AnkiCardUpdate, {"target_1": None}),
    ],
)
def test_patch_rejects_null_for_required_columns(schema, payload) -> None:
    with pytest.raises(ValidationError, match="cannot be null"):
        schema.model_validate(payload)


def test_patch_allows_clearing_optional_fields() -> None:
    update = AnkiCardUpdate.model_validate({"reading": None, "example_base": None})
    assert update.model_fields_set == {"reading", "example_base"}
    assert AnkibookUpdate.model_validate({"description": None}).description is None


def test_card_text_is_bounded() -> None:
    with pytest.raises(ValidationError):
        AnkiCardCreate(base_text="x" * (CARD_TEXT_MAX + 1), target_1="y")


def test_bulk_size_is_bounded() -> None:
    card = {"base_text": "a", "target_1": "b"}
    AnkiCardBulkCreate.model_validate({"cards": [card] * BULK_CARDS_MAX})
    with pytest.raises(ValidationError):
        AnkiCardBulkCreate.model_validate({"cards": [card] * (BULK_CARDS_MAX + 1)})


def test_lection_position_is_bounded() -> None:
    with pytest.raises(ValidationError):
        AnkilectionCreate(name="x", position=POSITION_MAX + 1)


def test_settings_are_safe_by_default() -> None:
    defaults = Settings(_env_file=None)
    assert defaults.ENVIRONMENT == "production"
    assert defaults.is_development is False
    assert defaults.DEBUG is False
    assert defaults.BACKEND_CORS_ORIGINS == []
