"""Data access repositories for AnkiBook."""

from app.repositories.ankibook import AnkibookRepository
from app.repositories.ankicard import AnkiCardRepository
from app.repositories.ankilection import AnkilectionRepository
from app.repositories.review import ReviewRepository
from app.repositories.user import UserRepository

__all__ = [
    "AnkibookRepository",
    "AnkiCardRepository",
    "AnkilectionRepository",
    "ReviewRepository",
    "UserRepository",
]
