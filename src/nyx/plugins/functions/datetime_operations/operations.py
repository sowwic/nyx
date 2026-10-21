"""Date and time functions. Moments are ISO 8601 text like `2026-10-21T18:15:00`."""

import calendar
import datetime

DEFAULT_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse(moment: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(moment)


def now() -> str:
    """Get the current local date and time."""
    return datetime.datetime.now().isoformat(timespec="seconds")


def utc_now() -> str:
    """Get the current date and time in UTC."""
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def today() -> str:
    """Get the current local date."""
    return datetime.date.today().isoformat()


def format_datetime(moment: str, pattern: str = DEFAULT_FORMAT) -> str:
    """Write a date and time with a pattern like "%Y-%m-%d %H:%M:%S".

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
        pattern: Pattern to write the date and time with.
    """
    return _parse(moment).strftime(pattern)


def parse_datetime(text: str, pattern: str = DEFAULT_FORMAT) -> str:
    """Read a date and time written with a pattern.

    Args:
        text: Date and time written with the pattern.
        pattern: Pattern the text is written with.
    """
    return datetime.datetime.strptime(text, pattern).isoformat()


def from_timestamp(seconds: float) -> str:
    """Convert the seconds since 1970-01-01 (UTC) to a date and time.

    Args:
        seconds: Seconds since 1970-01-01 (UTC).
    """
    return (
        datetime.datetime.fromtimestamp(seconds, datetime.UTC)
        .replace(tzinfo=None)
        .isoformat()
    )


def to_timestamp(moment: str) -> float:
    """Get the seconds since 1970-01-01 of a date and time, UTC without a timezone.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    parsed = _parse(moment)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.UTC)
    return parsed.timestamp()


def add_time(
    moment: str,
    days: float = 0,
    hours: float = 0,
    minutes: float = 0,
    seconds: float = 0,
) -> str:
    """Move a date and time later, or earlier with negative amounts.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
        days: Days to move.
        hours: Hours to move.
        minutes: Minutes to move.
        seconds: Seconds to move.
    """
    delta = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return (_parse(moment) + delta).isoformat()


def seconds_between(start: str, end: str) -> float:
    """Get the seconds from start to end, negative if end is earlier.

    Args:
        start: Date and time to count from.
        end: Date and time to count to.
    """
    return (_parse(end) - _parse(start)).total_seconds()


def days_between(start: str, end: str) -> int:
    """Get the whole days from the date of start to the date of end.

    Args:
        start: Date and time to count from.
        end: Date and time to count to.
    """
    return (_parse(end).date() - _parse(start).date()).days


def year(moment: str) -> int:
    """Get the year.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    return _parse(moment).year


def month(moment: str) -> int:
    """Get the month, 1 to 12.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    return _parse(moment).month


def day(moment: str) -> int:
    """Get the day of the month.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    return _parse(moment).day


def hour(moment: str) -> int:
    """Get the hour, 0 to 23.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    return _parse(moment).hour


def minute(moment: str) -> int:
    """Get the minute.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    return _parse(moment).minute


def second(moment: str) -> int:
    """Get the second.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    return _parse(moment).second


def weekday(moment: str) -> int:
    """Get the day of the week, 0 for Monday up to 6 for Sunday.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    return _parse(moment).weekday()


def weekday_name(moment: str) -> str:
    """Get the name of the day of the week.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    return calendar.day_name[_parse(moment).weekday()]


def day_of_year(moment: str) -> int:
    """Get the day of the year, 1 for January 1st.

    Args:
        moment: Date and time as ISO text, like 2026-10-21T18:15:00.
    """
    return _parse(moment).timetuple().tm_yday


def is_leap_year(year: int) -> bool:
    """Check if a year has a February 29th.

    Args:
        year: Year to check.
    """
    return calendar.isleap(year)


def days_in_month(year: int, month: int) -> int:
    """Get the number of days in a month.

    Args:
        year: Year of the month.
        month: Month, 1 to 12.
    """
    return calendar.monthrange(year, month)[1]
