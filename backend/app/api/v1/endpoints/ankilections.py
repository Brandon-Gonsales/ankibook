import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.ankilection import AnkilectionRepository
from app.schemas.ankilection import (
    AnkilectionCreate,
    AnkilectionDetail,
    AnkilectionRead,
    AnkilectionUpdate,
)


router = APIRouter(tags=["Ankilections"])
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/ankibooks/{book_id}/lections",
    response_model=AnkilectionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_ankilection(
    book_id: uuid.UUID,
    data: AnkilectionCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> AnkilectionRead:
    repository = AnkilectionRepository(session)
    try:
        lection = await repository.create(current_user.id, book_id, data)
        if lection is None:
            raise HTTPException(status_code=404, detail="Ankibook not found")
        await session.commit()
    except HTTPException:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise
    return AnkilectionRead.model_validate(lection)


@router.get(
    "/ankibooks/{book_id}/lections",
    response_model=list[AnkilectionRead],
)
async def list_ankilections(
    book_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> list[AnkilectionRead]:
    return await AnkilectionRepository(session).list_for_book(
        current_user.id,
        book_id,
    )


@router.get("/lections/{lection_id}", response_model=AnkilectionDetail)
async def get_ankilection(
    lection_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> AnkilectionDetail:
    lection = await AnkilectionRepository(session).get_detail(
        current_user.id,
        lection_id,
    )
    if lection is None:
        raise HTTPException(status_code=404, detail="Ankilection not found")
    return lection


@router.patch("/lections/{lection_id}", response_model=AnkilectionRead)
async def update_ankilection(
    lection_id: uuid.UUID,
    data: AnkilectionUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> AnkilectionRead:
    repository = AnkilectionRepository(session)
    lection = await repository.get_owned(current_user.id, lection_id)
    if lection is None:
        raise HTTPException(status_code=404, detail="Ankilection not found")
    try:
        lection = await repository.update(lection, data)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return AnkilectionRead.model_validate(lection)


@router.delete("/lections/{lection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ankilection(
    lection_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> Response:
    repository = AnkilectionRepository(session)
    lection = await repository.get_owned(current_user.id, lection_id)
    if lection is None:
        raise HTTPException(status_code=404, detail="Ankilection not found")
    try:
        await repository.delete(lection)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
