"""Calendar of the study day: when "today" starts for the user.

The day does not roll over at midnight but at ``SRS_DAY_START_HOUR`` in
``SRS_TIMEZONE`` (like Anki), so a session at 00:30 still counts as the
previous day.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings


def study_day_start(
    now: datetime,
    *,
    tz_name: str | None = None,
    start_hour: int | None = None,
) -> datetime:
    """Return, in UTC, the moment the study day containing ``now`` began."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    tz = ZoneInfo(tz_name or settings.SRS_TIMEZONE)
    hour = settings.SRS_DAY_START_HOUR if start_hour is None else start_hour
    local = now.astimezone(tz)
    start = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if local < start:
        start -= timedelta(days=1)
    return start.astimezone(timezone.utc)


def next_study_day_start(
    now: datetime,
    *,
    tz_name: str | None = None,
    start_hour: int | None = None,
) -> datetime:
    """Return, in UTC, the moment tomorrow's study day begins."""
    tz = ZoneInfo(tz_name or settings.SRS_TIMEZONE)
    start = study_day_start(now, tz_name=tz_name, start_hour=start_hour)
    # Add a calendar day in local time so zones with DST keep the wall clock.
    return (start.astimezone(tz) + timedelta(days=1)).astimezone(timezone.utc)
