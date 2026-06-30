"""
Display a candlestick chart for one downloaded XAU/USD CSV file.

Usage:
    python chart.py 2024-01-26
    python chart.py 2024-01-26 --dark
    python chart.py 2024-01-26 --sessions
    python chart.py 2024-01-26 --dark --sessions
"""

from __future__ import annotations

import csv
import json
import math
import sys
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from candle_filters import is_flat_zero_volume_candle, remove_edge_inactive_placeholders

# Matplotlib is imported later, after we know the CSV file exists. This keeps
# missing-file errors fast and easy to understand.
mdates = None
plt = None
Rectangle = None


SYMBOL = "XAUUSD"
TIMEFRAME_LABEL = "1min"
PRICE_SIDE = "BID"

PROJECT_DIR = Path(__file__).resolve().parent
DATA_RAW_DIR = PROJECT_DIR / "data_raw"
SESSIONS_CONFIG_PATH = PROJECT_DIR / "sessions.json"


@dataclass
class Candle:
    """One row of candle data from the CSV file."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class ChartStyle:
    """Colours and styling choices for the chart."""

    figure_background: str
    chart_background: str
    text: str
    grid: str
    bullish: str
    bearish: str
    annotation_background: str
    annotation_edge: str


@dataclass
class ChartArguments:
    """Command-line options for the chart viewer."""

    day: date
    dark_mode: bool
    show_sessions: bool


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
    """One session window converted into naive UTC timestamps for plotting."""

    name: str
    start_utc: datetime
    end_utc: datetime
    color: str


def parse_day(day_text: str) -> date:
    """Convert text like '2024-01-26' into a Python date."""
    try:
        return datetime.strptime(day_text, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("Please enter the date in YYYY-MM-DD format.") from error


def parse_arguments(arguments: list[str]) -> ChartArguments:
    """Read the date and optional chart flags from the command line."""
    if len(arguments) not in (1, 2, 3):
        raise ValueError("Please enter one date, with optional --dark and --sessions.")

    allowed_flags = {"--dark", "--sessions"}
    flags = arguments[1:]
    unknown_flags = [flag for flag in flags if flag not in allowed_flags]

    if unknown_flags:
        raise ValueError(f"Unknown chart option: {unknown_flags[0]}")

    if len(flags) != len(set(flags)):
        raise ValueError("Please do not repeat chart options.")

    return ChartArguments(
        day=parse_day(arguments[0]),
        dark_mode="--dark" in flags,
        show_sessions="--sessions" in flags,
    )


def build_csv_path(day: date) -> Path:
    """Build the expected CSV path for one downloaded day."""
    filename = f"{SYMBOL}_{day:%Y-%m-%d}_{TIMEFRAME_LABEL}_{PRICE_SIDE}_UTC.csv"
    return DATA_RAW_DIR / filename


def load_candles(csv_path: Path) -> list[Candle]:
    """Load candlestick data from a CSV file."""
    candles = []

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            candle = Candle(
                timestamp=datetime.strptime(row["timestamp_utc"], "%Y-%m-%d %H:%M:%S"),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            candles.append(candle)

    if not candles:
        raise ValueError("The CSV file does not contain any candle rows.")

    return candles


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
    """Convert one local session definition into UTC timestamps for the chart."""
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


def is_inactive_placeholder_candle(candle: Candle) -> bool:
    """Return True if a candle is a flat, zero-volume placeholder row."""
    return is_flat_zero_volume_candle(
        candle.open,
        candle.high,
        candle.low,
        candle.close,
        candle.volume,
    )


def get_active_candle_result(candles: list[Candle]):
    """Remove only leading/trailing inactive placeholders from chart data."""
    return remove_edge_inactive_placeholders(candles, is_inactive_placeholder_candle)


def check_matplotlib_is_available() -> bool:
    """Return True when matplotlib was imported successfully."""
    global mdates, plt, Rectangle

    try:
        import matplotlib.dates as matplotlib_dates
        import matplotlib.pyplot as pyplot
        from matplotlib.patches import Rectangle as MatplotlibRectangle
    except ModuleNotFoundError:
        print("Matplotlib is required to display charts.")
        print("Install it with: python -m pip install matplotlib")
        return False

    mdates = matplotlib_dates
    plt = pyplot
    Rectangle = MatplotlibRectangle
    return True


def matplotlib_is_loaded() -> bool:
    """Return True after matplotlib has been imported."""
    return plt is not None and mdates is not None and Rectangle is not None


def get_chart_style(dark_mode: bool) -> ChartStyle:
    """Choose readable colours for light mode or dark mode."""
    if dark_mode:
        return ChartStyle(
            figure_background="#0f172a",
            chart_background="#111827",
            text="#e5e7eb",
            grid="#475569",
            bullish="#22c55e",
            bearish="#f87171",
            annotation_background="#1f2937",
            annotation_edge="#94a3b8",
        )

    return ChartStyle(
        figure_background="#f8fafc",
        chart_background="#ffffff",
        text="#111827",
        grid="#cbd5e1",
        bullish="#15803d",
        bearish="#b91c1c",
        annotation_background="#ffffff",
        annotation_edge="#475569",
    )


def candle_colour(candle: Candle, style: ChartStyle) -> str:
    """Return the bullish or bearish colour for one candle."""
    if candle.close >= candle.open:
        return style.bullish

    return style.bearish


def draw_candles(ax, candles: list[Candle], style: ChartStyle) -> None:
    """Draw candlestick bodies and wicks onto the chart."""
    if not matplotlib_is_loaded():
        raise RuntimeError("Matplotlib was not loaded before drawing the chart.")

    # Matplotlib stores dates as numbers. One full day is 1.0, so one minute
    # is 1 / (24 * 60). A slightly narrower width leaves space between candles.
    candle_width = 0.7 / (24 * 60)

    for candle in candles:
        candle_time = mdates.date2num(candle.timestamp)
        candle_color = candle_colour(candle, style)

        # The wick is the thin line from the candle low to the candle high.
        ax.vlines(
            candle_time,
            candle.low,
            candle.high,
            color=candle_color,
            linewidth=0.6,
        )

        body_bottom = min(candle.open, candle.close)
        body_height = abs(candle.close - candle.open)

        if body_height == 0:
            # If open and close are the same, draw a small flat line.
            ax.hlines(
                candle.open,
                candle_time - candle_width / 2,
                candle_time + candle_width / 2,
                color=candle_color,
                linewidth=0.8,
            )
        else:
            body = Rectangle(
                (candle_time - candle_width / 2, body_bottom),
                candle_width,
                body_height,
                facecolor=candle_color,
                edgecolor=candle_color,
                linewidth=0.4,
            )
            ax.add_patch(body)


def calculate_price_limits(candles: list[Candle]) -> tuple[float, float]:
    """Calculate y-axis limits from candle highs and lows only."""
    lowest_price = min(candle.low for candle in candles)
    highest_price = max(candle.high for candle in candles)
    price_range = highest_price - lowest_price

    if price_range == 0:
        # If the market somehow did not move, still leave visible space.
        padding = max(abs(highest_price) * 0.001, 1.0)
    else:
        padding = price_range * 0.08

    return lowest_price - padding, highest_price + padding


def style_chart_axes(ax, style: ChartStyle) -> None:
    """Apply spacing, gridlines, and colours to the chart axes."""
    ax.set_facecolor(style.chart_background)
    ax.tick_params(axis="both", colors=style.text)
    ax.xaxis.label.set_color(style.text)
    ax.yaxis.label.set_color(style.text)
    ax.title.set_color(style.text)

    for spine in ax.spines.values():
        spine.set_color(style.grid)

    ax.grid(True, which="major", linestyle="-", linewidth=0.7, alpha=0.55, color=style.grid)
    ax.grid(True, which="minor", linestyle=":", linewidth=0.45, alpha=0.35, color=style.grid)
    ax.set_axisbelow(True)


def draw_session_overlays(ax, session_windows: list[SessionWindow], style: ChartStyle) -> None:
    """Draw subtle shaded research-session windows behind the candles."""
    for session in session_windows:
        ax.axvspan(
            session.start_utc,
            session.end_utc,
            color=session.color,
            alpha=0.13,
            linewidth=0,
            zorder=0,
        )

        label_time = session.start_utc + (session.end_utc - session.start_utc) / 2
        ax.text(
            label_time,
            0.98,
            session.name,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=8,
            color=style.text,
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": style.annotation_background,
                "edgecolor": session.color,
                "alpha": 0.85,
            },
            zorder=5,
        )


def format_hover_text(candle: Candle) -> str:
    """Build the text shown when the mouse hovers near a candle."""
    return (
        f"{candle.timestamp:%Y-%m-%d %H:%M:%S} UTC\n"
        f"Open:  {candle.open:.3f}\n"
        f"High:  {candle.high:.3f}\n"
        f"Low:   {candle.low:.3f}\n"
        f"Close: {candle.close:.3f}"
    )


def nearest_candle_index(candle_times: list[float], mouse_x: float) -> int:
    """Find the candle closest to the mouse's x-axis position."""
    position = bisect_left(candle_times, mouse_x)
    candidates = []

    if position < len(candle_times):
        candidates.append(position)

    if position > 0:
        candidates.append(position - 1)

    return min(candidates, key=lambda index: abs(candle_times[index] - mouse_x))


def add_hover_cursor(fig, ax, candles: list[Candle], style: ChartStyle) -> None:
    """Show candle OHLC information when the mouse is near a candle."""
    candle_times = [mdates.date2num(candle.timestamp) for candle in candles]
    one_minute = 1 / (24 * 60)
    hidden_value = math.nan

    annotation = ax.annotate(
        "",
        xy=(hidden_value, hidden_value),
        xytext=(15, 15),
        textcoords="offset points",
        color=style.text,
        bbox={
            "boxstyle": "round,pad=0.45",
            "facecolor": style.annotation_background,
            "edgecolor": style.annotation_edge,
            "alpha": 0.95,
        },
        arrowprops={"arrowstyle": "->", "color": style.annotation_edge},
    )
    annotation.set_visible(False)

    # Start hover lines at NaN coordinates so they never affect autoscaling.
    vertical_line = ax.plot(
        [hidden_value, hidden_value],
        [hidden_value, hidden_value],
        color=style.annotation_edge,
        linewidth=0.7,
        alpha=0.65,
    )[0]
    horizontal_line = ax.plot(
        [hidden_value, hidden_value],
        [hidden_value, hidden_value],
        color=style.annotation_edge,
        linewidth=0.7,
        alpha=0.65,
    )[0]
    vertical_line.set_visible(False)
    horizontal_line.set_visible(False)

    def hide_hover_items() -> None:
        annotation.set_visible(False)
        vertical_line.set_visible(False)
        horizontal_line.set_visible(False)

    def on_mouse_move(event) -> None:
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            if annotation.get_visible():
                hide_hover_items()
                fig.canvas.draw_idle()
            return

        index = nearest_candle_index(candle_times, event.xdata)

        # Only show the label when the mouse is close to a candle.
        if abs(candle_times[index] - event.xdata) > one_minute:
            if annotation.get_visible():
                hide_hover_items()
                fig.canvas.draw_idle()
            return

        candle = candles[index]
        candle_time = candle_times[index]
        candle_midpoint = (candle.open + candle.close) / 2
        current_x_limits = ax.get_xlim()
        current_y_limits = ax.get_ylim()

        annotation.xy = (candle_time, candle_midpoint)
        annotation.set_text(format_hover_text(candle))
        annotation.set_visible(True)

        # Use the current visible limits so zooming and panning still work.
        vertical_line.set_data([candle_time, candle_time], list(current_y_limits))
        horizontal_line.set_data(list(current_x_limits), [candle_midpoint, candle_midpoint])
        vertical_line.set_visible(True)
        horizontal_line.set_visible(True)

        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_mouse_move)


def create_chart_figure(
    day: date,
    candles: list[Candle],
    dark_mode: bool = False,
    show_sessions: bool = False,
):
    """Create the chart figure and axes."""
    if not matplotlib_is_loaded():
        raise RuntimeError("Matplotlib was not loaded before creating the chart.")

    active_result = get_active_candle_result(candles)
    active_candles = active_result.active_rows

    if not active_candles:
        raise ValueError("The CSV file does not contain any active candle rows.")

    style = get_chart_style(dark_mode)
    fig, ax = plt.subplots(figsize=(15, 8))
    fig.patch.set_facecolor(style.figure_background)

    draw_candles(ax, active_candles, style)

    ax.set_title(f"XAU/USD 1-Minute BID Candlestick Chart - {day:%Y-%m-%d}")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Price (USD)")

    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    x_limits = (
        active_candles[0].timestamp,
        active_candles[-1].timestamp + timedelta(minutes=1),
    )
    y_limits = calculate_price_limits(active_candles)
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)

    style_chart_axes(ax, style)

    if show_sessions:
        session_windows = get_session_windows(day)
        draw_session_overlays(ax, session_windows, style)

    add_hover_cursor(fig, ax, active_candles, style)

    # Session overlays and hover artists must not expand the chart limits.
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)

    fig.autofmt_xdate()
    fig.tight_layout(pad=2.0)
    return fig, ax


def display_chart(
    day: date,
    candles: list[Candle],
    dark_mode: bool = False,
    show_sessions: bool = False,
) -> None:
    """Create and display the candlestick chart."""
    create_chart_figure(day, candles, dark_mode, show_sessions)
    plt.show()


def print_usage() -> None:
    """Print the correct command format."""
    print("Usage: python chart.py YYYY-MM-DD [--dark] [--sessions]")
    print("Example: python chart.py 2024-01-26")
    print("Example: python chart.py 2024-01-26 --dark")
    print("Example: python chart.py 2024-01-26 --sessions")
    print("Example: python chart.py 2024-01-26 --dark --sessions")


def main() -> int:
    """Run the chart viewer from the command line."""
    if len(sys.argv) not in (2, 3, 4):
        print_usage()
        return 1

    try:
        chart_arguments = parse_arguments(sys.argv[1:])
        requested_day = chart_arguments.day
        csv_path = build_csv_path(requested_day)

        if not csv_path.exists():
            print(f"No downloaded CSV was found for {requested_day:%Y-%m-%d}.")
            print(f"Expected file: {csv_path}")
            print("Download that day first, then run the chart viewer again.")
            return 1

        if not check_matplotlib_is_available():
            return 1

        candles = load_candles(csv_path)
        display_chart(
            requested_day,
            candles,
            chart_arguments.dark_mode,
            chart_arguments.show_sessions,
        )
        return 0

    except ValueError as error:
        print(f"Input error: {error}")
        return 1
    except KeyError as error:
        print(f"CSV error: missing expected column {error}.")
        return 1
    except OSError as error:
        print(f"File error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
