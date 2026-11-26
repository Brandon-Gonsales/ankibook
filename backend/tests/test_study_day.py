from datetime import date, datetime, timezone

import pytest

from app.services.study_day import (
    next_study_day_start,
    streak_length,
    study_date,
    study_day_start,
)

TZ = "America/La_Paz"  # UTC-4, no DST


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def test_day_starts_at_4am_local_time() -> None:
    # 10:00 in Santa Cruz (14:00 UTC) -> the day began at 04:00 local (08:00 UTC)
    assert study_day_start(utc(2026, 11, 26, 14), tz_name=TZ, start_hour=4) == utc(2026, 11, 26, 8)


def test_after_midnight_still_counts_as_previous_day() -> None:
    # 00:30 in Santa Cruz on the 27th (04:30 UTC) is still the study day of the 26th
    now = utc(2026, 11, 27, 4, 30)
    assert study_day_start(now, tz_name=TZ, start_hour=4) == utc(2026, 11, 26, 8)
    assert next_study_day_start(now, tz_name=TZ, start_hour=4) == utc(2026, 11, 27, 8)


def test_exactly_at_rollover_belongs_to_new_day() -> None:
    now = utc(2026, 11, 27, 8)
    assert study_day_start(now, tz_name=TZ, start_hour=4) == now
    assert next_study_day_start(now, tz_name=TZ, start_hour=4) == utc(2026, 11, 28, 8)


def test_study_date_names_the_day_by_its_local_date() -> None:
    assert study_date(utc(2026, 11, 27, 4, 30), tz_name=TZ, start_hour=4) == date(2026, 11, 26)
    assert study_date(utc(2026, 11, 27, 8, 0), tz_name=TZ, start_hour=4) == date(2026, 11, 27)


def test_streak_counts_consecutive_days_up_to_today() -> None:
    days = {date(2026, 11, 24), date(2026, 11, 25), date(2026, 11, 26)}
    assert streak_length(days, date(2026, 11, 26)) == 3


def test_streak_survives_while_today_is_pending() -> None:
    days = {date(2026, 11, 24), date(2026, 11, 25)}
    assert streak_length(days, date(2026, 11, 26)) == 2


def test_streak_breaks_after_a_missed_day() -> None:
    days = {date(2026, 11, 20), date(2026, 11, 21), date(2026, 11, 26)}
    assert streak_length(days, date(2026, 11, 26)) == 1
    assert streak_length({date(2026, 11, 24)}, date(2026, 11, 26)) == 0
    assert streak_length(set(), date(2026, 11, 26)) == 0


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        study_day_start(datetime(2026, 11, 26, 12), tz_name=TZ, start_hour=4)
