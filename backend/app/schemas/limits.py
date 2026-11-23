"""Shared size limits and validators for request payloads.

Limits keep a single request from storing unbounded text; they are generous
for vocabulary cards but stop accidental or abusive multi-megabyte payloads.
"""

from collections.abc import Iterable

from pydantic import BaseModel

TITLE_MAX = 255
DESCRIPTION_MAX = 2000
CARD_TEXT_MAX = 500
EXAMPLE_MAX = 1000
READING_MAX = 255
BULK_CARDS_MAX = 1000
POSITION_MAX = 10_000


def reject_explicit_nulls(model: BaseModel, fields: Iterable[str]) -> None:
    """Raise when a PATCH payload sends ``null`` for a NOT NULL column.

    Omitting a field leaves it unchanged; sending ``null`` would try to store
    NULL and fail in the database, so it is rejected as a validation error.
    """
    for field in fields:
        if field in model.model_fields_set and getattr(model, field) is None:
            raise ValueError(f"{field} cannot be null")
