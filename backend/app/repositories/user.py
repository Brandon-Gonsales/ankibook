from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.user import User


class UserRepository:
    """Persistence operations for Firebase-backed users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: str) -> User | None:
        return (
            await self.session.exec(select(User).where(User.id == user_id))
        ).one_or_none()

    async def get_or_create(self, user_id: str) -> User:
        """Provision a UID safely when concurrent authenticated requests arrive."""
        statement = (
            insert(User)
            .values(id=user_id)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await self.session.exec(statement)
        return (await self.session.exec(select(User).where(User.id == user_id))).one()
