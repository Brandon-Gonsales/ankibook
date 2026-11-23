import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.ankibook import AnkibookRepository
from app.schemas.ankibook import (
    AnkibookCreate,
    AnkibookDetail,
    AnkibookRead,
    AnkibookUpdate,
)


router = APIRouter(prefix="/ankibooks", tags=["Ankibooks"])
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=AnkibookRead, status_code=status.HTTP_201_CREATED)
async def create_ankibook(
    data: AnkibookCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> AnkibookRead:
    repository = AnkibookRepository(session)
    try:
        book = await repository.create(current_user.id, data)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return AnkibookRead.model_validate({**book.model_dump(), "is_owner": True})


@router.get("", response_model=list[AnkibookRead])
async def list_ankibooks(
    current_user: CurrentUser,
    session: DBSession,
) -> list[AnkibookRead]:
    return await AnkibookRepository(session).list_for_user(current_user.id)


@router.get("/explore", response_model=list[AnkibookRead])
async def explore_ankibooks(
    current_user: CurrentUser,
    session: DBSession,
) -> list[AnkibookRead]:
    """Every public book, flagged with is_owner / is_added for the caller."""
    return await AnkibookRepository(session).list_public(current_user.id)


@router.put("/{book_id}/library", status_code=status.HTTP_204_NO_CONTENT)
async def add_to_library(
    book_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> Response:
    """Add someone else's book to the caller's study library (idempotent)."""
    repository = AnkibookRepository(session)
    if not await repository.exists(book_id):
        raise HTTPException(status_code=404, detail="Ankibook not found")
    if await repository.get_owned(current_user.id, book_id) is None:
        try:
            await repository.add_to_library(current_user.id, book_id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{book_id}/library", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_library(
    book_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> Response:
    """Stop studying a book; the caller's review history is kept."""
    repository = AnkibookRepository(session)
    try:
        await repository.remove_from_library(current_user.id, book_id)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{book_id}", response_model=AnkibookDetail)
async def get_ankibook(
    book_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> AnkibookDetail:
    book = await AnkibookRepository(session).get_detail(current_user.id, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Ankibook not found")
    return book


@router.patch("/{book_id}", response_model=AnkibookRead)
async def update_ankibook(
    book_id: uuid.UUID,
    data: AnkibookUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> AnkibookRead:
    repository = AnkibookRepository(session)
    book = await repository.get_owned(current_user.id, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Ankibook not found")

    target_lang = data.target_lang if data.target_lang is not None else book.target_lang
    base_lang = data.base_lang if data.base_lang is not None else book.base_lang
    if target_lang.casefold() == base_lang.casefold():
        raise HTTPException(
            status_code=422,
            detail="target_lang must be different from base_lang",
        )

    try:
        book = await repository.update(book, data)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return AnkibookRead.model_validate({**book.model_dump(), "is_owner": True})


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ankibook(
    book_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> Response:
    repository = AnkibookRepository(session)
    book = await repository.get_owned(current_user.id, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Ankibook not found")
    try:
        await repository.delete(book)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
