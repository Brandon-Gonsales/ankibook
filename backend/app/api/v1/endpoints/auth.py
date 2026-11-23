from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserRead


router = APIRouter(prefix="/auth", tags=["Authentication"])
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: CurrentUser) -> UserRead:
    """Validate the Firebase ID Token and return its provisioned user."""
    return UserRead.model_validate(current_user)
