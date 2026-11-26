import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Date, and_, case, cast, distinct, exists, func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased
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
from app.schemas.review_log import BookProgressRead, DueCardRead
from app.schemas.user_card_progress import UserCardProgressRead


# A card the user never reviewed has no progress row, or a "new" row created
# only to bury it until tomorrow.
_HAS_PROGRESS = UserCardProgress.id.is_not(None)
IS_NEW = or_(UserCardProgress.id.is_(None), UserCardProgress.state == CardState.NEW.value)
IS_SEEN = and_(_HAS_PROGRESS, UserCardProgress.state != CardState.NEW.value)
IS_LEARNING = UserCardProgress.state.in_(
    [CardState.LEARNING.value, CardState.RELEARNING.value]
)


def _new_available(now: datetime):
    """New card that is not buried past ``now``."""
    return or_(
        UserCardProgress.id.is_(None),
        and_(UserCardProgress.state == CardState.NEW.value, UserCardProgress.due <= now),
    )


def _seen_due(now: datetime):
    return and_(IS_SEEN, UserCardProgress.due <= now)


@dataclass(slots=True)
class StudyCounts:
    """Raw per-user aggregates used to build the study summary."""

    due_now: int = 0
    due_before_horizon: int = 0
    next_due: datetime | None = None
    new_available: int = 0
    new_remaining: int = 0
    books: list[BookProgressRead] = field(default_factory=list)


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
        new_limit: int | None = None,
    ) -> list[DueCardRead]:
        """Fetch the cards to study now, with book/lesson context.

        Seen cards come first (being (re)learned, then due reviews, oldest
        first), followed by new cards in lesson order. ``new_limit`` caps the
        new cards (``None`` = no cap, used when studying one book or lesson).
        Buried cards (due later) are skipped in every mode.
        """
        due_at = due_at or datetime.now(timezone.utc)

        seen_statement = (
            self._study_statement(user_id, book_id=book_id, lection_id=lection_id)
            .where(_seen_due(due_at))
            .order_by(
                case((IS_LEARNING, 0), else_=1),
                UserCardProgress.due.asc(),
                Ankilection.position,
                AnkiCard.created_at,
            )
            .limit(limit)
        )
        rows = list((await self.session.exec(seen_statement)).all())

        room = limit - len(rows)
        if new_limit is not None:
            room = min(room, new_limit)
        if room > 0:
            new_statement = (
                self._study_statement(user_id, book_id=book_id, lection_id=lection_id)
                .where(_new_available(due_at))
                # Lesson order across books: lesson 1 of every book, then 2...
                .order_by(
                    Ankilection.position,
                    Ankibook.created_at,
                    Ankilection.id,
                    AnkiCard.created_at,
                    AnkiCard.id,
                )
                .limit(room)
            )
            rows.extend((await self.session.exec(new_statement)).all())

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
                target_lang=target_lang,
            )
            for card, progress, lection_id, lection_name, book_id, book_title, target_lang in rows
        ]

    async def count_new_started_since(self, user_id: str, since: datetime) -> int:
        """Cards whose very first review happened at or after ``since``."""
        earlier = aliased(ReviewLog)
        statement = select(func.count(distinct(ReviewLog.ankicard_id))).where(
            ReviewLog.user_id == user_id,
            ReviewLog.reviewed_at >= since,
            ~exists().where(
                earlier.user_id == user_id,
                earlier.ankicard_id == ReviewLog.ankicard_id,
                earlier.reviewed_at < since,
            ),
        )
        return int((await self.session.exec(statement)).one() or 0)

    async def count_reviews_since(self, user_id: str, since: datetime) -> int:
        statement = select(func.count(ReviewLog.id)).where(
            ReviewLog.user_id == user_id,
            ReviewLog.reviewed_at >= since,
        )
        return int((await self.session.exec(statement)).one() or 0)

    async def study_dates_since(
        self,
        user_id: str,
        since: datetime,
        *,
        tz_name: str,
        day_start_hour: int,
    ) -> set[date]:
        """Local study days (rolling over at ``day_start_hour``) with a review."""
        local_day = cast(
            func.timezone(tz_name, ReviewLog.reviewed_at) - timedelta(hours=day_start_hour),
            Date,
        )
        statement = (
            select(local_day)
            .where(ReviewLog.user_id == user_id, ReviewLog.reviewed_at >= since)
            .distinct()
        )
        return set((await self.session.exec(statement)).all())

    async def study_counts(
        self,
        user_id: str,
        *,
        now: datetime,
        horizon: datetime,
    ) -> StudyCounts:
        """Aggregate the user's cards per book in a single query.

        ``horizon`` bounds the "due before" count used to forecast tomorrow.
        """
        seen_due_later = and_(IS_SEEN, UserCardProgress.due > now)
        statement = (
            select(
                Ankibook.id,
                func.count(AnkiCard.id),
                func.count(AnkiCard.id).filter(IS_NEW),
                func.count(AnkiCard.id).filter(and_(_HAS_PROGRESS, IS_LEARNING)),
                func.count(AnkiCard.id).filter(
                    UserCardProgress.state == CardState.REVIEW.value
                ),
                func.count(AnkiCard.id).filter(_seen_due(now)),
                func.count(AnkiCard.id).filter(
                    and_(IS_SEEN, UserCardProgress.due < horizon)
                ),
                func.min(UserCardProgress.due).filter(seen_due_later),
                func.count(AnkiCard.id).filter(_new_available(now)),
            )
            .select_from(AnkiCard)
            .join(Ankilection, AnkiCard.ankilection_id == Ankilection.id)
            .join(Ankibook, Ankilection.ankibook_id == Ankibook.id)
            .outerjoin(
                UserCardProgress,
                and_(
                    UserCardProgress.ankicard_id == AnkiCard.id,
                    UserCardProgress.user_id == user_id,
                ),
            )
            .where(studied_by(user_id))
            .group_by(Ankibook.id)
        )
        counts = StudyCounts()
        for (
            book_id,
            total,
            new,
            learning,
            learned,
            due_now,
            due_before,
            next_due,
            new_available,
        ) in (await self.session.exec(statement)).all():
            counts.books.append(
                BookProgressRead(
                    book_id=book_id,
                    total=total,
                    new=new,
                    learning=learning,
                    learned=learned,
                )
            )
            counts.due_now += due_now
            counts.due_before_horizon += due_before
            counts.new_available += new_available
            counts.new_remaining += new
            if next_due is not None and (counts.next_due is None or next_due < counts.next_due):
                counts.next_due = next_due
        return counts

    def add_review_log(self, review_log: ReviewLog) -> None:
        self.session.add(review_log)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    @staticmethod
    def _study_statement(
        user_id: str,
        *,
        book_id: uuid.UUID | None,
        lection_id: uuid.UUID | None,
    ):
        """Cards of the books the user studies, with their progress (if any)."""
        statement = (
            select(
                AnkiCard,
                UserCardProgress,
                Ankilection.id.label("lection_id"),
                Ankilection.name.label("lection_name"),
                Ankibook.id.label("book_id"),
                Ankibook.title.label("book_title"),
                Ankibook.target_lang.label("target_lang"),
            )
            .join(Ankilection, AnkiCard.ankilection_id == Ankilection.id)
            .join(Ankibook, Ankilection.ankibook_id == Ankibook.id)
            .outerjoin(
                UserCardProgress,
                and_(
                    UserCardProgress.ankicard_id == AnkiCard.id,
                    UserCardProgress.user_id == user_id,
                ),
            )
            .where(studied_by(user_id))
        )
        if book_id is not None:
            statement = statement.where(Ankibook.id == book_id)
        if lection_id is not None:
            statement = statement.where(Ankilection.id == lection_id)
        return statement
