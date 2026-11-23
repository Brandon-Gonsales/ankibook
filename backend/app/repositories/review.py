import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, case, or_
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.ankibook import Ankibook
from app.models.ankicard import AnkiCard
from app.models.ankilection import Ankilection
from app.models.enums import CardState
from app.models.review_log import ReviewLog
from app.repositories.ankibook import studied_by
from app.models.user_card_progress import UserCardProgress
from app.schemas.ankicard import AnkiCardRead
from app.schemas.review_log import DueCardRead
from app.schemas.user_card_progress import UserCardProgressRead


class ReviewRepository:
    """Persistence operations required by review sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_owned_card(
        self,
        user_id: str,
        card_id: uuid.UUID,
    ) -> AnkiCard | None:
        """Return a card only from a book the user authored or added."""
        statement = (
            select(AnkiCard)
            .join(Ankilection, AnkiCard.ankilection_id == Ankilection.id)
            .join(Ankibook, Ankilection.ankibook_id == Ankibook.id)
            .where(AnkiCard.id == card_id, studied_by(user_id))
        )
        return (await self.session.exec(statement)).one_or_none()

    async def get_or_create_progress_for_update(
        self,
        user_id: str,
        card_id: uuid.UUID,
    ) -> UserCardProgress:
        """Create missing progress and lock it against concurrent reviews."""
        statement = (
            insert(UserCardProgress)
            .values(user_id=user_id, ankicard_id=card_id)
            .on_conflict_do_nothing(index_elements=["user_id", "ankicard_id"])
        )
        await self.session.exec(statement)

        progress_statement = (
            select(UserCardProgress)
            .where(
                UserCardProgress.user_id == user_id,
                UserCardProgress.ankicard_id == card_id,
            )
            .with_for_update()
        )
        return (await self.session.exec(progress_statement)).one()

    async def list_due_cards(
        self,
        user_id: str,
        *,
        due_at: datetime | None = None,
        limit: int = 20,
        book_id: uuid.UUID | None = None,
        lection_id: uuid.UUID | None = None,
    ) -> list[DueCardRead]:
        """Fetch the cards to study now, with book/lesson context, in one query.

        * General review (no scope): only cards already seen that are due.
          New cards never flood it; they are introduced per book or lesson.
        * Scoped to a book or lesson: due cards plus that scope's new cards.

        Order: cards being (re)learned first, then due reviews, then new cards.
        """
        due_at = due_at or datetime.now(timezone.utc)
        is_new = UserCardProgress.id.is_(None)
        is_due = and_(UserCardProgress.id.is_not(None), UserCardProgress.due <= due_at)
        scoped = book_id is not None or lection_id is not None
        priority = case(
            (is_new, 2),
            (
                UserCardProgress.state.in_(
                    [CardState.LEARNING.value, CardState.RELEARNING.value]
                ),
                0,
            ),
            else_=1,
        )
        progress_join = and_(
            UserCardProgress.ankicard_id == AnkiCard.id,
            UserCardProgress.user_id == user_id,
        )
        statement = (
            select(
                AnkiCard,
                UserCardProgress,
                Ankilection.id.label("lection_id"),
                Ankilection.name.label("lection_name"),
                Ankibook.id.label("book_id"),
                Ankibook.title.label("book_title"),
            )
            .join(Ankilection, AnkiCard.ankilection_id == Ankilection.id)
            .join(Ankibook, Ankilection.ankibook_id == Ankibook.id)
            .outerjoin(UserCardProgress, progress_join)
            .where(
                studied_by(user_id),
                or_(is_new, is_due) if scoped else is_due,
            )
            .order_by(
                priority,
                UserCardProgress.due.asc().nullslast(),
                Ankilection.position,
                AnkiCard.created_at,
            )
            .limit(limit)
        )
        if book_id is not None:
            statement = statement.where(Ankibook.id == book_id)
        if lection_id is not None:
            statement = statement.where(Ankilection.id == lection_id)
        rows = (await self.session.exec(statement)).all()
        return [
            DueCardRead(
                card=AnkiCardRead.model_validate(card),
                progress=(
                    UserCardProgressRead.model_validate(progress)
                    if progress is not None
                    else None
                ),
                lection_id=lection_id,
                lection_name=lection_name,
                book_id=book_id,
                book_title=book_title,
            )
            for card, progress, lection_id, lection_name, book_id, book_title in rows
        ]

    def add_review_log(self, review_log: ReviewLog) -> None:
        self.session.add(review_log)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
