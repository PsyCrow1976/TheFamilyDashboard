"""Read one Google Calendar over its secret iCal address. Nothing is stored."""

from __future__ import annotations

import os
import threading
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import recurring_ical_events
from icalendar import Calendar

TIMEZONE = ZoneInfo("Europe/Copenhagen")
REFRESH_SECONDS = 5 * 60
STALE_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT = 12


@dataclass(frozen=True)
class AgendaEvent:
    title: str
    start: datetime
    end: datetime
    all_day: bool
    location: str


@dataclass(frozen=True)
class Agenda:
    first: list[AgendaEvent]
    second: list[AgendaEvent]
    calendar_name: str | None
    error: str | None
    stale: bool


@dataclass
class _CachedFeed:
    fetched_at: datetime
    calendar: Calendar
    name: str | None


_lock = threading.Lock()
_cached: _CachedFeed | None = None
_last_error: str | None = None


def load_agenda(now: datetime, first_day: date | None = None) -> Agenda:
    """Events overlapping two days starting at first_day. Uses the last feed when refresh fails."""
    url = os.environ.get("GOOGLE_CALENDAR_ICS_URL", "").strip()
    if not url:
        return Agenda(
            [],
            [],
            None,
            "Add GOOGLE_CALENDAR_ICS_URL to the environment. In Google Calendar, "
            "open that calendar’s settings and copy the secret iCal address.",
            False,
        )

    start = first_day or now.date()
    following = start + timedelta(days=1)
    try:
        feed, error, stale = _feed(url, now)
        if feed is None:
            return Agenda([], [], None, error, False)

        window_start = datetime.combine(start, time.min, tzinfo=TIMEZONE)
        window_end = datetime.combine(following + timedelta(days=1), time.min, tzinfo=TIMEZONE)
        events = _events_overlapping(feed.calendar, window_start, window_end)
    except Exception as exc:
        return Agenda([], [], None, _safe_error(exc, url), False)
    return Agenda(
        first=_on_day(events, start),
        second=_on_day(events, following),
        calendar_name=feed.name,
        error=error,
        stale=stale,
    )


def _feed(url: str, now: datetime) -> tuple[_CachedFeed | None, str | None, bool]:
    global _cached, _last_error
    with _lock:
        fresh = (
            _cached is not None
            and (now - _cached.fetched_at).total_seconds() < REFRESH_SECONDS
        )
        if fresh:
            return _cached, None, False
        try:
            payload = _download(url)
            calendar = Calendar.from_ical(payload)
            if not isinstance(calendar, Calendar):
                raise ValueError("Calendar feed was empty")
            calendar = _without_overflowing_events(calendar)
            _cached = _CachedFeed(
                fetched_at=now,
                calendar=calendar,
                name=_calendar_name(calendar),
            )
            _last_error = None
            return _cached, None, False
        except Exception as exc:
            message = _safe_error(exc, url)
            _last_error = message
            if _cached is not None and (now - _cached.fetched_at).total_seconds() < STALE_SECONDS:
                return _cached, message, True
            return None, message, False


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TheFamilyDashboard/0.0.8"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def _events_overlapping(
    calendar: Calendar, window_start: datetime, window_end: datetime
) -> list[AgendaEvent]:
    found: list[AgendaEvent] = []
    series = recurring_ical_events.of(calendar, skip_bad_series=True)
    for component in series.between(window_start, window_end):
        try:
            status = str(component.get("STATUS") or "")
            if status.upper() == "CANCELLED":
                continue
            start_raw = component.get("DTSTART")
            if start_raw is None or not hasattr(start_raw, "dt"):
                continue
            end_raw = component.get("DTEND")
            end_dt = end_raw.dt if end_raw is not None and hasattr(end_raw, "dt") else None
            start, end, all_day = _span(start_raw.dt, end_dt)
            if end <= window_start or start >= window_end:
                continue
            title = str(component.get("SUMMARY") or "").strip() or "(No title)"
            location = str(component.get("LOCATION") or "").strip()
        except (OverflowError, TypeError, ValueError):
            continue
        found.append(
            AgendaEvent(
                title=title,
                start=start,
                end=end,
                all_day=all_day,
                location=location,
            )
        )
    return found


def _span(start_dt: date | datetime, end_dt: date | datetime | None) -> tuple[datetime, datetime, bool]:
    all_day = isinstance(start_dt, date) and not isinstance(start_dt, datetime)
    if all_day:
        start = datetime.combine(start_dt, time.min, tzinfo=TIMEZONE)
        if isinstance(end_dt, date) and not isinstance(end_dt, datetime):
            end = datetime.combine(end_dt, time.min, tzinfo=TIMEZONE)
        else:
            end = start + timedelta(days=1)
        if end <= start:
            end = start + timedelta(days=1)
        return start, end, True

    start = _as_local(start_dt)
    if isinstance(end_dt, datetime):
        end = _as_local(end_dt)
    elif isinstance(end_dt, date):
        end = datetime.combine(end_dt, time.min, tzinfo=TIMEZONE)
    else:
        end = start + timedelta(hours=1)
    if end <= start:
        end = start + timedelta(hours=1)
    return start, end, False


def _as_local(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=TIMEZONE)
    return value.astimezone(TIMEZONE)


def _on_day(events: list[AgendaEvent], day: date) -> list[AgendaEvent]:
    start = datetime.combine(day, time.min, tzinfo=TIMEZONE)
    end = start + timedelta(days=1)
    chosen = [event for event in events if event.start < end and event.end > start]
    chosen.sort(key=lambda event: (0 if event.all_day else 1, event.start, event.title.casefold()))
    return chosen


def _without_overflowing_events(calendar: Calendar) -> Calendar:
    """Drop events whose timestamps cannot be shifted into local time.

    Google sometimes stores a placeholder at 9999-12-31 23:00 UTC. Moving that
    into Europe/Copenhagen overflows datetime and used to crash the whole page.
    """
    kept = []
    dropped = False
    for component in calendar.subcomponents:
        if component.name == "VEVENT" and not _event_dates_fit(component):
            dropped = True
            continue
        kept.append(component)
    if not dropped:
        return calendar
    clone = Calendar()
    for key, value in calendar.items():
        clone.add(key, value)
    for component in kept:
        clone.add_component(component)
    return clone


def _event_dates_fit(component) -> bool:
    for prop in ("DTSTART", "DTEND", "RDATE", "RECURRENCE-ID", "EXDATE"):
        if prop not in component:
            continue
        value = component.get(prop)
        raw = getattr(value, "dts", None)
        if raw is not None:
            instants = [item.dt for item in raw]
        elif hasattr(value, "dt"):
            instants = [value.dt]
        else:
            continue
        for instant in instants:
            if isinstance(instant, datetime) and not _fits_local(instant):
                return False
    return True


def _fits_local(instant: datetime) -> bool:
    if instant.year >= 9999 or instant.year < 1:
        return False
    if instant.tzinfo is None:
        return True
    try:
        instant.astimezone(TIMEZONE)
    except (OverflowError, OSError, ValueError):
        return False
    return True


def _calendar_name(calendar: Calendar) -> str | None:
    raw = calendar.get("X-WR-CALNAME")
    if raw is None:
        return None
    name = str(raw).strip()
    return name or None


def _safe_error(exc: Exception, url: str) -> str:
    text = f"{exc.__class__.__name__}: {exc}"
    if url:
        text = text.replace(url, "the calendar address")
    return text
