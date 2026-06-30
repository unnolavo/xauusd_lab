"""
Reusable helpers for configurable research-session windows.

Session definitions live in sessions.json in local time zones. These helpers
convert those local windows into UTC for a selected trading date, then select
and summarise candles that fall inside each session.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PROJECT_DIR = Path(__file__).resolve().parent
SESSIONS_CONFIG_PATH = PROJECT_DIR / "sessions.json"


@dataclass
class SessionDefinition:
    """One configurable trading-session research window."""

    name: str
    timezone_name: str
    local_start: time
    local_end: time
    color: str


@dataclass
class SessionWindow:
    """One session window converted into UTC timestamps."""

    name: str
    timezone_name: str
    local_start: time
    local_end: time
    start_utc: datetime
    end_utc: datetime
    color: str


@dataclass
class CandleData:
    """Simple candle shape used by session statistics."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class SessionStatistics:
    """Statistics for active candles inside one session window."""

    session_name: str
    timezone_name: str
    local_start: time
    local_end: time
    start_utc: datetime
    end_utc: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    range_dollars: float | None
    time_of_high_utc: datetime | None
    time_of_low_utc: datetime | None
    time_of_high_local: datetime | None
    time_of_low_local: datetime | None
    active_candle_count: int

    @property
    def has_active_candles(self) -> bool:
        """Return True when the session contains at least one active candle."""
        return self.active_candle_count > 0


def parse_session_time(time_text: str) -> time:
    """Convert session time text like '09:00' into a Python time."""
    try:
        return datetime.strptime(time_text, "%H:%M").time()
    except ValueError as error:
        raise ValueError(f"Session time must use HH:MM format: {time_text}") from error


def load_session_definitions(
    config_path: Path = SESSIONS_CONFIG_PATH,
) -> list[SessionDefinition]:
    """Load configurable research-session windows from sessions.json."""
    if not config_path.exists():
        raise ValueError(f"Could not find session config file: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError as error:
        raise ValueError(f"sessions.json is not valid JSON: {error}") from error

    sessions = config.get("sessions")

    if not isinstance(sessions, list) or not sessions:
        raise ValueError("sessions.json must contain a non-empty 'sessions' list.")

    definitions = []

    for session in sessions:
        if not isinstance(session, dict):
            raise ValueError("Each session entry must be a JSON object.")

        try:
            name = str(session["name"])
            timezone_name = str(session["timezone"])
            local_start = parse_session_time(str(session["local_start"]))
            local_end = parse_session_time(str(session["local_end"]))
            color = str(session["color"])
        except KeyError as error:
            raise ValueError(f"Session entry is missing required field: {error}") from error

        definitions.append(
            SessionDefinition(
                name=name,
                timezone_name=timezone_name,
                local_start=local_start,
                local_end=local_end,
                color=color,
            )
        )

    return definitions


def convert_session_to_utc_window(
    trading_day: date,
    session: SessionDefinition,
) -> SessionWindow:
    """Convert one local session definition into UTC timestamps."""
    try:
        session_timezone = ZoneInfo(session.timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(
            f"Could not load timezone '{session.timezone_name}'. "
            "On Windows, install timezone data with: python -m pip install tzdata"
        ) from error

    local_start = datetime.combine(
        trading_day,
        session.local_start,
        tzinfo=session_timezone,
    )
    local_end = datetime.combine(
        trading_day,
        session.local_end,
        tzinfo=session_timezone,
    )

    if local_end <= local_start:
        local_end += timedelta(days=1)

    start_utc = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = local_end.astimezone(timezone.utc).replace(tzinfo=None)

    return SessionWindow(
        name=session.name,
        timezone_name=session.timezone_name,
        local_start=session.local_start,
        local_end=session.local_end,
        start_utc=start_utc,
        end_utc=end_utc,
        color=session.color,
    )


def get_session_windows(trading_day: date) -> list[SessionWindow]:
    """Load session definitions and convert them to UTC windows."""
    definitions = load_session_definitions()
    return [
        convert_session_to_utc_window(trading_day, definition)
        for definition in definitions
    ]


def utc_to_session_local(utc_timestamp: datetime, timezone_name: str) -> datetime:
    """Convert a naive UTC timestamp into a session's local timezone."""
    try:
        session_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(
            f"Could not load timezone '{timezone_name}'. "
            "On Windows, install timezone data with: python -m pip install tzdata"
        ) from error

    aware_utc_timestamp = utc_timestamp.replace(tzinfo=timezone.utc)
    return aware_utc_timestamp.astimezone(session_timezone)


def select_candles_for_session(
    candles: list[CandleData],
    session_window: SessionWindow,
) -> list[CandleData]:
    """Select candles using a start-inclusive, end-exclusive UTC window."""
    return [
        candle
        for candle in candles
        if session_window.start_utc <= candle.timestamp < session_window.end_utc
    ]


def calculate_session_statistics(
    candles: list[CandleData],
    session_window: SessionWindow,
) -> SessionStatistics:
    """Calculate OHLC and range statistics for one session window."""
    session_candles = select_candles_for_session(candles, session_window)

    if not session_candles:
        return SessionStatistics(
            session_name=session_window.name,
            timezone_name=session_window.timezone_name,
            local_start=session_window.local_start,
            local_end=session_window.local_end,
            start_utc=session_window.start_utc,
            end_utc=session_window.end_utc,
            open=None,
            high=None,
            low=None,
            close=None,
            range_dollars=None,
            time_of_high_utc=None,
            time_of_low_utc=None,
            time_of_high_local=None,
            time_of_low_local=None,
            active_candle_count=0,
        )

    first_candle = session_candles[0]
    last_candle = session_candles[-1]
    high_candle = max(session_candles, key=lambda candle: candle.high)
    low_candle = min(session_candles, key=lambda candle: candle.low)
    time_of_high_local = utc_to_session_local(
        high_candle.timestamp,
        session_window.timezone_name,
    )
    time_of_low_local = utc_to_session_local(
        low_candle.timestamp,
        session_window.timezone_name,
    )

    return SessionStatistics(
        session_name=session_window.name,
        timezone_name=session_window.timezone_name,
        local_start=session_window.local_start,
        local_end=session_window.local_end,
        start_utc=session_window.start_utc,
        end_utc=session_window.end_utc,
        open=first_candle.open,
        high=high_candle.high,
        low=low_candle.low,
        close=last_candle.close,
        range_dollars=high_candle.high - low_candle.low,
        time_of_high_utc=high_candle.timestamp,
        time_of_low_utc=low_candle.timestamp,
        time_of_high_local=time_of_high_local,
        time_of_low_local=time_of_low_local,
        active_candle_count=len(session_candles),
    )
