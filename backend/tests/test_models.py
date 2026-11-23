import uuid
from app.models import (
    CardState,
    ReviewDirection,
    User,
    Ankibook,
    Ankilection,
    AnkiCard,
    UserCardProgress,
    ReviewLog,
)


def test_user_model_instantiation() -> None:
    """Test User model can be instantiated with Firebase UID only."""
    firebase_uid = "firebase_uid_test_12345"
    user = User(id=firebase_uid)
    assert user.id == firebase_uid
    assert user.ankibooks == []


def test_ankibook_model_instantiation() -> None:
    """Test Ankibook model with defaults and relations."""
    book = Ankibook(
        author_id="firebase_user_1",
        title="Japanese for Beginners",
        target_lang="ja",
        base_lang="es",
    )
    assert isinstance(book.id, uuid.UUID)
    assert book.author_id == "firebase_user_1"
    assert book.title == "Japanese for Beginners"
    assert book.target_lang == "ja"
    assert book.base_lang == "es"
    assert book.created_at is not None


def test_ankilection_model_instantiation() -> None:
    """Test Ankilection model fields and defaults."""
    book_id = uuid.uuid4()
    lection = Ankilection(
        ankibook_id=book_id,
        name="Lesson 1: Greetings",
        position=1,
    )
    assert isinstance(lection.id, uuid.UUID)
    assert lection.ankibook_id == book_id
    assert lection.name == "Lesson 1: Greetings"
    assert lection.position == 1


def test_ankicard_model_instantiation() -> None:
    """Test AnkiCard model with target translations and examples."""
    lection_id = uuid.uuid4()
    card = AnkiCard(
        ankilection_id=lection_id,
        base_text="Hola",
        target_1="Hello",
        target_2="Hi",
        reading=None,
        example_base="Hola mundo",
        example_target_1="Hello world",
        example_target_2="Hi world",
    )
    assert isinstance(card.id, uuid.UUID)
    assert card.ankilection_id == lection_id
    assert card.base_text == "Hola"
    assert card.target_1 == "Hello"
    assert card.target_2 == "Hi"
    assert card.target_3 is None
    assert card.example_base == "Hola mundo"
    assert card.example_target_1 == "Hello world"
    assert card.example_target_2 == "Hi world"
    assert card.example_target_3 is None


def test_user_card_progress_model_instantiation() -> None:
    """Test UserCardProgress model defaults."""
    card_id = uuid.uuid4()
    progress = UserCardProgress(
        user_id="firebase_user_1",
        ankicard_id=card_id,
        state=CardState.NEW.value,
    )
    assert isinstance(progress.id, uuid.UUID)
    assert progress.user_id == "firebase_user_1"
    assert progress.ankicard_id == card_id
    assert progress.state == "new"
    assert progress.interval_days == 0.0
    assert progress.ease == 2.5
    assert progress.reps == 0
    assert progress.lapses == 0
    assert progress.due is not None


def test_review_log_model_instantiation() -> None:
    """Test ReviewLog model fields and values."""
    card_id = uuid.uuid4()
    log = ReviewLog(
        user_id="firebase_user_1",
        ankicard_id=card_id,
        direction=ReviewDirection.BASE_TO_TARGET.value,
        rating=3,
    )
    assert log.id is None  # BigInteger autoincrement primary key set upon DB insert
    assert log.user_id == "firebase_user_1"
    assert log.ankicard_id == card_id
    assert log.direction == "base_to_target"
    assert log.rating == 3
    assert log.reviewed_at is not None
