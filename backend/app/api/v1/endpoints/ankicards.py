import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.ankicard import AnkiCardRepository
from app.schemas.ankicard import (
    AnkiCardBulkCreate,
    AnkiCardCreate,
    AnkiCardRead,
    AnkiCardUpdate,
)


router = APIRouter(tags=["AnkiCards"])
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/lections/{lection_id}/cards",
    response_model=AnkiCardRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_ankicard(
    lection_id: uuid.UUID,
    data: AnkiCardCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> AnkiCardRead:
    repository = AnkiCardRepository(session)
    try:
        card = await repository.create(current_user.id, lection_id, data)
        if card is None:
            raise HTTPException(status_code=404, detail="Ankilection not found")
        await session.commit()
    except HTTPException:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise
    return AnkiCardRead.model_validate(card)


@router.post(
    "/lections/{lection_id}/cards/bulk",
    response_model=list[AnkiCardRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_ankicards_bulk(
    lection_id: uuid.UUID,
    data: AnkiCardBulkCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> list[AnkiCardRead]:
    repository = AnkiCardRepository(session)
    try:
        cards = await repository.create_bulk(
            current_user.id,
            lection_id,
            data.cards,
        )
        if cards is None:
            raise HTTPException(status_code=404, detail="Ankilection not found")
        await session.commit()
    except HTTPException:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise
    return [AnkiCardRead.model_validate(card) for card in cards]


@router.get(
    "/lections/{lection_id}/cards",
    response_model=list[AnkiCardRead],
)
async def list_ankicards(
    lection_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> list[AnkiCardRead]:
    return await AnkiCardRepository(session).list_for_lection(
        current_user.id,
        lection_id,
    )


@router.get("/cards/{card_id}", response_model=AnkiCardRead)
async def get_ankicard(
    card_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> AnkiCardRead:
    card = await AnkiCardRepository(session).get_visible(card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="AnkiCard not found")
    return AnkiCardRead.model_validate(card)


@router.patch("/cards/{card_id}", response_model=AnkiCardRead)
async def update_ankicard(
    card_id: uuid.UUID,
    data: AnkiCardUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> AnkiCardRead:
    repository = AnkiCardRepository(session)
    card = await repository.get_owned(current_user.id, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="AnkiCard not found")

    # The patch alone can be valid while the resulting card is not
    # (e.g. target_3 set while the stored target_2 is empty).
    merged = {**card.model_dump(), **data.model_dump(exclude_unset=True)}
    try:
        AnkiCardRead.model_validate(merged)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": err["msg"], "loc": err["loc"]} for err in exc.errors()],
        ) from exc

    try:
        card = await repository.update(card, data)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return AnkiCardRead.model_validate(card)


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ankicard(
    card_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> Response:
    repository = AnkiCardRepository(session)
    card = await repository.get_owned(current_user.id, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="AnkiCard not found")
    try:
        await repository.delete(card)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
