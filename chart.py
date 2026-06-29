"""
Display a candlestick chart for one downloaded XAU/USD CSV file.

Usage:
    python chart.py 2024-01-26
    python chart.py 2024-01-26 --dark
"""

from __future__ import annotations

import csv
import math
import sys
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

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


@dataclass
class Candle:
    """One row of candle data from the CSV file."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


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


def parse_day(day_text: str) -> date:
    """Convert text like '2024-01-26' into a Python date."""
    try:
        return datetime.strptime(day_text, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("Please enter the date in YYYY-MM-DD format.") from error


def parse_arguments(arguments: list[str]) -> ChartArguments:
    """Read the date and optional --dark flag from the command line."""
    if len(arguments) not in (1, 2):
        raise ValueError("Please enter one date, with optional --dark.")

    if len(arguments) == 2 and arguments[1] != "--dark":
        raise ValueError("The only optional chart flag is --dark.")

    return ChartArguments(day=parse_day(arguments[0]), dark_mode="--dark" in arguments)


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
            )
            candles.append(candle)

    if not candles:
        raise ValueError("The CSV file does not contain any candle rows.")

    return candles


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


def create_chart_figure(day: date, candles: list[Candle], dark_mode: bool = False):
    """Create the chart figure and axes."""
    if not matplotlib_is_loaded():
        raise RuntimeError("Matplotlib was not loaded before creating the chart.")

    style = get_chart_style(dark_mode)
    fig, ax = plt.subplots(figsize=(15, 8))
    fig.patch.set_facecolor(style.figure_background)

    draw_candles(ax, candles, style)

    ax.set_title(f"XAU/USD 1-Minute BID Candlestick Chart - {day:%Y-%m-%d}")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Price (USD)")

    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    x_limits = (candles[0].timestamp, candles[-1].timestamp + timedelta(minutes=1))
    y_limits = calculate_price_limits(candles)
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)

    style_chart_axes(ax, style)
    add_hover_cursor(fig, ax, candles, style)

    # Hover artists must not expand the chart to zero or any other value.
    ax.set_xlim(*x_limits)
    ax.set_ylim(*y_limits)

    fig.autofmt_xdate()
    fig.tight_layout(pad=2.0)
    return fig, ax


def display_chart(day: date, candles: list[Candle], dark_mode: bool = False) -> None:
    """Create and display the candlestick chart."""
    create_chart_figure(day, candles, dark_mode)
    plt.show()


def print_usage() -> None:
    """Print the correct command format."""
    print("Usage: python chart.py YYYY-MM-DD [--dark]")
    print("Example: python chart.py 2024-01-26")
    print("Example: python chart.py 2024-01-26 --dark")


def main() -> int:
    """Run the chart viewer from the command line."""
    if len(sys.argv) not in (2, 3):
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
        display_chart(requested_day, candles, chart_arguments.dark_mode)
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
