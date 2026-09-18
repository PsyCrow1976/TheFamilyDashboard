"""FastHTML family dashboard for electricity prices and usage."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from fasthtml.common import (
    A,
    Div,
    H1,
    Header,
    Main,
    Nav,
    P,
    Script,
    Span,
    Style,
    Title,
    fast_app,
)
from starlette.responses import PlainTextResponse

from web import db

TIMEZONE = ZoneInfo("Europe/Copenhagen")
TAB_MS = 5 * 60 * 1000

CSS = """
:root {
  --bg: #14110e;
  --panel: #1f1a16;
  --ink: #f4efe6;
  --muted: #b3a99a;
  --line: #3a322b;
  --low: #3d9a5f;
  --mid: #d0892a;
  --high: #c44b3c;
  --now: #f4efe6;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--ink);
  font-family: "Segoe UI", "Helvetica Neue", sans-serif; overflow: hidden; }
body { padding: 0; }
a { color: inherit; }
.wrap { height: 100vh; height: 100dvh; display: flex; flex-direction: column;
  padding: 0.8rem 1.2rem 0.9rem; }
header.top { flex: 0 0 auto; display: flex; justify-content: space-between; align-items: end;
  gap: 1rem; flex-wrap: wrap; border-bottom: 1px solid var(--line); padding-bottom: 0.65rem; }
header.top h1 { margin: 0; font-size: clamp(1.4rem, 2.6vh, 2.2rem); letter-spacing: 0.02em; }
nav.tabs { display: flex; gap: 0.5rem; }
nav.tabs a { text-decoration: none; padding: 0.4rem 0.85rem; border-radius: 999px;
  border: 1px solid var(--line); color: var(--muted); font-weight: 650; }
nav.tabs a.active { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.panels { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.panel { display: none; flex: 1; min-height: 0; padding-top: 0.7rem; }
.wrap[data-tab="prices"] .panel-prices,
.wrap[data-tab="usage"] .panel-usage { display: flex; flex-direction: column; gap: 0.55rem; }
.hero { flex: 0 0 auto; display: flex; flex-direction: column; gap: 0.1rem; }
.hero .nums { display: flex; gap: 2.4rem; flex-wrap: wrap; align-items: baseline; }
.big { font-size: clamp(1.7rem, 5.5vh, 4.2rem); font-weight: 750; line-height: 0.95;
  font-variant-numeric: tabular-nums; letter-spacing: -0.03em; }
.big .unit { font-size: 0.32em; font-weight: 650; color: var(--muted); margin-left: 0.25rem;
  letter-spacing: 0; }
.sub { color: var(--muted); margin: 0.15rem 0 0; font-size: clamp(0.85rem, 1.6vh, 1.05rem); }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; flex: 1; min-height: 0; }
@media (max-width: 800px) { .pair { grid-template-columns: 1fr; } }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 1rem;
  padding: 0.55rem 0.7rem 0.5rem; display: flex; flex-direction: column; min-height: 0; }
.card-title { flex: 0 0 auto; font-weight: 650; }
.card .when { flex: 0 0 auto; color: var(--muted); margin: 0.05rem 0 0.35rem; font-size: 0.88rem; }
.chart { display: flex; flex-direction: column; flex: 1; min-height: 0; gap: 0.08rem; }
.row { display: grid; grid-template-columns: 3.4rem minmax(0, 1fr) 3.4rem;
  align-items: center; gap: 0.4rem; padding: 0 0.15rem; border-radius: 0.3rem;
  flex: 1 1 0; min-height: 0; }
.row.now { background: #2c2620; outline: 1px solid var(--now); }
.row .hour { color: var(--muted); font-variant-numeric: tabular-nums;
  font-size: clamp(0.62rem, 1.5vh, 0.85rem); }
.row.now .hour { color: var(--ink); font-weight: 650; }
.track { height: 58%; min-height: 4px; background: #2a241f; border-radius: 999px; overflow: hidden; }
.fill { height: 100%; width: 100%;
  background: linear-gradient(90deg, var(--low) 0%, var(--mid) 50%, var(--high) 100%);
  clip-path: inset(0 calc(100% - var(--w, 0%)) 0 0); }
.row .val { text-align: right; font-variant-numeric: tabular-nums;
  font-size: clamp(0.62rem, 1.5vh, 0.85rem); font-weight: 650; }
.empty-msg { color: var(--muted); margin: auto 0; }
.legend { flex: 0 0 auto; display: flex; align-items: center; gap: 0.55rem; color: var(--muted);
  font-size: 0.88rem; flex-wrap: wrap; }
.legend-bar { width: 8rem; height: 0.5rem; border-radius: 999px;
  background: linear-gradient(90deg, var(--low) 0%, var(--mid) 50%, var(--high) 100%); }
.day-nav { flex: 0 0 auto; display: flex; justify-content: space-between; align-items: center;
  gap: 0.8rem; }
.day-nav a, .day-nav .disabled { text-decoration: none; padding: 0.4rem 0.85rem;
  border-radius: 999px; font-weight: 650; border: 1px solid var(--line); }
.day-nav a:hover { border-color: var(--ink); }
.day-nav .disabled { color: #6a635a; border-color: transparent; }
.day-nav .current { color: var(--muted); font-variant-numeric: tabular-nums; }
.warn { flex: 0 0 auto; background: #3a2a1c; border: 1px solid #7a5a32;
  border-radius: 0.7rem; padding: 0.7rem 1rem; }
"""

JS = f"""
(() => {{
  const wrap = document.querySelector(".wrap");
  document.querySelectorAll("nav.tabs a").forEach((link) => {{
    link.addEventListener("click", (event) => {{
      const tab = link.dataset.tab;
      if (!tab || !wrap) return;
      event.preventDefault();
      wrap.dataset.tab = tab;
      document.querySelectorAll("nav.tabs a").forEach((item) => {{
        item.classList.toggle("active", item.dataset.tab === tab);
      }});
      const params = new URLSearchParams(location.search);
      params.set("tab", tab);
      if (tab !== "usage") params.delete("day");
      history.replaceState(null, "", "/?" + params.toString());
    }});
  }});
  setTimeout(() => {{
    const current = wrap && wrap.dataset.tab === "usage" ? "usage" : "prices";
    location.assign("/?tab=" + (current === "prices" ? "usage" : "prices"));
  }}, {TAB_MS});
}})();
"""


app, rt = fast_app(
    title="The Family Dashboard",
    pico=False,
    hdrs=(Style(CSS),),
)


@rt("/health")
def health() -> PlainTextResponse:
    return PlainTextResponse("ok")


@rt("/")
def index(tab: str | None = None, day: str | None = None):
    chosen = "usage" if tab == "usage" else "prices"
    now = datetime.now(TIMEZONE)
    today = now.date()
    tomorrow = today + timedelta(days=1)
    error = None
    today_hours: list[db.PriceHour] = []
    tomorrow_hours: list[db.PriceHour] = []
    usage_hours: list[db.UsageHour] = []
    usage_day: date | None = None
    latest_usage: date | None = None
    prev_usage: date | None = None
    next_usage: date | None = None
    try:
        today_hours = db.list_price_hours(today)
        tomorrow_hours = db.list_price_hours(tomorrow)
        latest_usage = db.latest_usage_date()
        usage_day = _parse_day(day) or latest_usage
        if usage_day:
            usage_hours = db.list_usage_hours(usage_day)
            prev_usage, next_usage = db.neighboring_usage_dates(usage_day)
    except Exception as exc:
        error = str(exc)

    current = next(
        (
            item
            for item in today_hours
            if item.local_hour == now.hour
        ),
        None,
    )
    price_values = [item.total_incl_vat for item in today_hours + tomorrow_hours]
    price_max = _max_decimal(price_values)

    usage_total = sum((item.usage_kwh for item in usage_hours), Decimal("0"))
    priced = [item.cost_dkk for item in usage_hours if item.cost_dkk is not None]
    cost_total = sum(priced, Decimal("0")) if priced else None
    missing_price = any(item.cost_dkk is None for item in usage_hours)

    body = []
    if error:
        body.append(Div(P(f"Could not read PostgreSQL: {error}"), cls="warn"))

    body.append(
        Div(
            Div(
                _hero(
                    [(fmt_kr(current.total_incl_vat) if current else "—", "kr/kWh")],
                    _current_caption(now, current),
                ),
                _legend(),
                Div(
                    _price_card("Today", today, today_hours, price_max, now),
                    _price_card("Tomorrow", tomorrow, tomorrow_hours, price_max, None),
                    cls="pair",
                ),
                cls="panel panel-prices",
            ),
            Div(
                _hero(
                    [
                        (fmt_kwh(usage_total) if usage_hours else "—", "kWh"),
                        (fmt_kr(cost_total) if cost_total is not None else "—", "kr"),
                    ],
                    _usage_caption(usage_day, latest_usage, missing_price),
                ),
                _legend(),
                Div(
                    _usage_card("Usage", usage_hours, "usage"),
                    _usage_card("Spent", usage_hours, "cost"),
                    cls="pair",
                ),
                _day_nav(usage_day, prev_usage, next_usage),
                cls="panel panel-usage",
            ),
            cls="panels",
        )
    )
    return (
        Title("The Family Dashboard"),
        Main(
            Header(
                H1("The Family Dashboard"),
                Nav(
                    _tab("prices", "Current prices", chosen),
                    _tab("usage", "Power usage", chosen),
                    cls="tabs",
                ),
                cls="top",
            ),
            *body,
            Script(JS),
            cls="wrap",
            data_tab=chosen,
        ),
    )


def _tab(name: str, label: str, chosen: str):
    return A(
        label,
        href=f"/?tab={name}",
        cls="active" if name == chosen else None,
        data_tab=name,
    )


def _hero(items: list[tuple[str, str]], caption: str):
    numbers = [
        Div(
            Span(value),
            Span(unit, cls="unit"),
            cls="big",
        )
        for value, unit in items
    ]
    return Div(
        Div(*numbers, cls="nums"),
        P(caption, cls="sub"),
        cls="hero",
    )


def _legend():
    return Div(
        Span("Low"),
        Span(cls="legend-bar"),
        Span("High"),
        cls="legend",
    )


def _day_nav(day: date | None, prev_day: date | None, next_day: date | None):
    if day is None:
        return None
    back = (
        A("← Previous day", href=f"/?tab=usage&day={prev_day.isoformat()}")
        if prev_day
        else Span("← Previous day", cls="disabled")
    )
    forward = (
        A("Next day →", href=f"/?tab=usage&day={next_day.isoformat()}")
        if next_day
        else Span("Next day →", cls="disabled")
    )
    return Div(
        back,
        Span(fmt_day(day), cls="current"),
        forward,
        cls="day-nav",
    )


def _price_card(
    title: str,
    day: date,
    hours: list[db.PriceHour],
    vmax: Decimal | None,
    now: datetime | None,
):
    if not hours:
        message = (
            "Tomorrow’s prices are not stored yet. They usually arrive after 13:00."
            if title == "Tomorrow"
            else "No prices stored for this date."
        )
        return Div(
            Div(title, cls="card-title"),
            P(fmt_day(day), cls="when"),
            P(message, cls="empty-msg"),
            cls="card",
        )
    current_hour = now.hour if now and now.date() == day else None
    rows = [
        _hour_row(
            hour=item.local_hour,
            value=item.total_incl_vat,
            shown=fmt_kr(item.total_incl_vat),
            vmax=vmax,
            is_now=current_hour is not None and item.local_hour == current_hour,
        )
        for item in hours
    ]
    return Div(
        Div(title, cls="card-title"),
        P(fmt_day(day), cls="when"),
        Div(*rows, cls="chart"),
        cls="card",
    )


def _usage_card(title: str, hours: list[db.UsageHour], kind: str):
    if not hours:
        return Div(
            Div(title, cls="card-title"),
            P("No hourly usage stored yet.", cls="empty-msg"),
            cls="card",
        )
    if kind == "cost":
        values = [item.cost_dkk for item in hours]
        vmax = _max_decimal([item for item in values if item is not None])
        format_value = fmt_kr
    else:
        values = [item.usage_kwh for item in hours]
        vmax = _max_decimal(values)
        format_value = fmt_kwh
    rows = [
        _hour_row(
            hour=item.local_hour,
            value=value,
            shown=format_value(value) if value is not None else "—",
            vmax=vmax,
            is_now=False,
        )
        for item, value in zip(hours, values)
    ]
    return Div(
        Div(title, cls="card-title"),
        P("per hour", cls="when"),
        Div(*rows, cls="chart"),
        cls="card",
    )


def _hour_row(
    *,
    hour: int,
    value: Decimal | None,
    shown: str,
    vmax: Decimal | None,
    is_now: bool,
):
    pct = 0 if value is None else _pct(value, vmax)
    return Div(
        Span(fmt_hour_range(hour), cls="hour"),
        Div(Div(cls="fill"), cls="track", style=f"--w:{pct}%"),
        Span(shown, cls="val"),
        cls="row now" if is_now else "row",
    )


def _current_caption(now: datetime, current: db.PriceHour | None) -> str:
    window = fmt_hour_range(now.hour)
    if current is None:
        return f"No stored price for {window} today"
    return f"This hour  {window}  ·  {fmt_day(now.date())}"


def _usage_caption(day: date | None, latest: date | None, missing_price: bool) -> str:
    if day is None:
        return "No usage stored yet"
    extra = "  ·  some hours have no matching price" if missing_price else ""
    label = "Latest day with usage" if latest and day == latest else "Usage"
    return f"{label}  {fmt_day(day)}{extra}"


def _parse_day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _pct(value: Decimal, vmax: Decimal | None) -> int:
    if vmax is None or vmax <= 0:
        return 8
    pct = int((value / vmax * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))
    if value > 0:
        return max(pct, 4)
    return 0


def _max_decimal(values: list[Decimal] | None) -> Decimal | None:
    nums = [item for item in (values or []) if item is not None]
    return max(nums) if nums else None


def fmt_kr(value: Decimal | float | None) -> str:
    if value is None:
        return "—"
    number = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{number:.2f}".replace(".", ",")


def fmt_kwh(value: Decimal | float | None) -> str:
    if value is None:
        return "—"
    number = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{number:.2f}".replace(".", ",")


def fmt_day(value: date) -> str:
    return value.strftime("%d %b %Y")


def fmt_hour_range(hour: int) -> str:
    return f"{hour:02d}-{hour + 1:02d}"
