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
html, body { margin: 0; min-height: 100%; background: var(--bg); color: var(--ink);
  font-family: "Segoe UI", "Helvetica Neue", sans-serif; }
body { padding: 0; }
a { color: inherit; }
.wrap { min-height: 100vh; display: flex; flex-direction: column; padding: 1.1rem 1.4rem 1.4rem; }
header.top { display: flex; justify-content: space-between; align-items: end;
  gap: 1rem; flex-wrap: wrap; border-bottom: 1px solid var(--line); padding-bottom: 0.8rem; }
header.top h1 { margin: 0; font-size: clamp(1.6rem, 3vw, 2.4rem); letter-spacing: 0.02em; }
nav.tabs { display: flex; gap: 0.5rem; }
nav.tabs a { text-decoration: none; padding: 0.45rem 0.9rem; border-radius: 999px;
  border: 1px solid var(--line); color: var(--muted); font-weight: 650; }
nav.tabs a.active { background: var(--ink); color: var(--bg); border-color: var(--ink); }
.panel { display: none; flex: 1; padding-top: 1.1rem; }
.wrap[data-tab="prices"] .panel-prices,
.wrap[data-tab="usage"] .panel-usage { display: flex; flex-direction: column; gap: 1rem; }
.hero { display: flex; flex-direction: column; gap: 0.2rem; }
.hero .nums { display: flex; gap: 2.4rem; flex-wrap: wrap; align-items: baseline; }
.big { font-size: clamp(2.4rem, 7vw, 5.2rem); font-weight: 750; line-height: 0.95;
  font-variant-numeric: tabular-nums; letter-spacing: -0.03em; }
.big .unit { font-size: 0.32em; font-weight: 650; color: var(--muted); margin-left: 0.25rem;
  letter-spacing: 0; }
.sub { color: var(--muted); margin: 0.25rem 0 0; font-size: 1.05rem; }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; flex: 1; min-height: 0; }
@media (max-width: 800px) { .pair { grid-template-columns: 1fr; } }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 1rem;
  padding: 0.9rem 0.9rem 0.7rem; display: flex; flex-direction: column; min-height: 18rem; }
.card h2 { margin: 0 0 0.15rem; font-size: 1.05rem; }
.card .when { color: var(--muted); margin: 0 0 0.7rem; font-size: 0.92rem; }
.chart { display: flex; flex-direction: column; flex: 1; min-height: 14rem; }
.markers { display: flex; height: 1.1rem; }
.markers span { flex: 1; text-align: center; font-size: 0.85rem; line-height: 1; }
.markers .now-mark { color: var(--now); }
.bars { display: flex; align-items: flex-end; gap: 3px; flex: 1; min-height: 11rem; }
.bar { flex: 1; min-width: 0; border-radius: 4px 4px 0 0; min-height: 2px; position: relative; }
.bar.low { background: var(--low); }
.bar.mid { background: var(--mid); }
.bar.high { background: var(--high); }
.bar.empty { background: #2a241f; min-height: 2px; }
.bar.now { outline: 2px solid var(--now); outline-offset: 1px; }
.hours { display: flex; margin-top: 0.35rem; color: var(--muted); font-variant-numeric: tabular-nums;
  font-size: 0.75rem; }
.hours span { flex: 1; text-align: center; }
.empty-msg { color: var(--muted); margin: auto 0; }
.legend { display: flex; gap: 1rem; color: var(--muted); font-size: 0.9rem; flex-wrap: wrap; }
.dot { display: inline-block; width: 0.75rem; height: 0.75rem; border-radius: 2px;
  margin-right: 0.35rem; vertical-align: -1px; }
.dot.low { background: var(--low); }
.dot.mid { background: var(--mid); }
.dot.high { background: var(--high); }
.warn { background: #3a2a1c; border: 1px solid #7a5a32; border-radius: 0.7rem; padding: 0.8rem 1rem; }
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
      history.replaceState(null, "", "/?tab=" + tab);
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
def index(tab: str | None = None):
    chosen = "usage" if tab == "usage" else "prices"
    now = datetime.now(TIMEZONE)
    today = now.date()
    tomorrow = today + timedelta(days=1)
    error = None
    today_hours: list[db.PriceHour] = []
    tomorrow_hours: list[db.PriceHour] = []
    usage_hours: list[db.UsageHour] = []
    usage_day: date | None = None
    try:
        today_hours = db.list_price_hours(today)
        tomorrow_hours = db.list_price_hours(tomorrow)
        usage_day = db.latest_usage_date()
        if usage_day:
            usage_hours = db.list_usage_hours(usage_day)
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
    price_min = _min_decimal(price_values)

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
                _legend("Cheap", "Mid", "Expensive"),
                Div(
                    _price_card("Today", today, today_hours, price_min, price_max, now),
                    _price_card("Tomorrow", tomorrow, tomorrow_hours, price_min, price_max, None),
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
                    _usage_caption(usage_day, missing_price),
                ),
                _legend("Low", "Mid", "High"),
                Div(
                    _usage_card("Usage", usage_hours, "usage"),
                    _usage_card("Spent", usage_hours, "cost"),
                    cls="pair",
                ),
                cls="panel panel-usage",
            ),
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


def _legend(low: str, mid: str, high: str):
    return Div(
        Span(Span(cls="dot low"), " ", low),
        Span(Span(cls="dot mid"), " ", mid),
        Span(Span(cls="dot high"), " ", high),
        cls="legend",
    )


def _price_card(
    title: str,
    day: date,
    hours: list[db.PriceHour],
    vmin: Decimal | None,
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
            Div(title, style="font-weight:650"),
            P(fmt_day(day), cls="when"),
            P(message, cls="empty-msg"),
            cls="card",
        )
    current_hour = now.hour if now and now.date() == day else None
    bars = []
    markers = []
    labels = []
    for item in hours:
        is_now = current_hour is not None and item.local_hour == current_hour
        pct = _pct(item.total_incl_vat, vmax)
        klass = "bar " + _band(item.total_incl_vat, vmin, vmax)
        if is_now:
            klass += " now"
        bars.append(
            Div(
                cls=klass,
                style=f"height:{pct}%",
                title=f"{item.local_hour:02d}:00  {fmt_kr(item.total_incl_vat)} kr/kWh",
            )
        )
        markers.append(Span("▼" if is_now else "", cls="now-mark" if is_now else None))
        labels.append(Span(f"{item.local_hour:02d}" if item.local_hour % 3 == 0 else ""))
    return Div(
        Div(title, style="font-weight:650"),
        P(fmt_day(day), cls="when"),
        Div(
            Div(*markers, cls="markers"),
            Div(*bars, cls="bars"),
            Div(*labels, cls="hours"),
            cls="chart",
        ),
        cls="card",
    )


def _usage_card(title: str, hours: list[db.UsageHour], kind: str):
    if not hours:
        return Div(
            Div(title, style="font-weight:650"),
            P("No hourly usage stored yet.", cls="empty-msg"),
            cls="card",
        )
    if kind == "cost":
        values = [item.cost_dkk for item in hours]
        vmax = _max_decimal([item for item in values if item is not None])
        vmin = _min_decimal([item for item in values if item is not None])
    else:
        values = [item.usage_kwh for item in hours]
        vmax = _max_decimal(values)
        vmin = _min_decimal(values)
    bars = []
    labels = []
    for item, value in zip(hours, values):
        if value is None:
            bars.append(Div(cls="bar empty", title=f"{item.local_hour:02d}:00  no price"))
        else:
            pct = _pct(value, vmax)
            unit = "kr" if kind == "cost" else "kWh"
            shown = fmt_kr(value) if kind == "cost" else fmt_kwh(value)
            klass = "bar " + _band(value, vmin, vmax)
            bars.append(
                Div(
                    cls=klass,
                    style=f"height:{pct}%",
                    title=f"{item.local_hour:02d}:00  {shown} {unit}",
                )
            )
        labels.append(Span(f"{item.local_hour:02d}" if item.local_hour % 3 == 0 else ""))
    return Div(
        Div(title, style="font-weight:650"),
        P("per hour", cls="when"),
        Div(
            Div(*bars, cls="bars"),
            Div(*labels, cls="hours"),
            cls="chart",
        ),
        cls="card",
    )


def _current_caption(now: datetime, current: db.PriceHour | None) -> str:
    window = f"{now.hour:02d}:00–{(now.hour + 1) % 24:02d}:00"
    if current is None:
        return f"No stored price for {window} today"
    return f"This hour  {window}  ·  {fmt_day(now.date())}"


def _usage_caption(day: date | None, missing_price: bool) -> str:
    if day is None:
        return "No usage stored yet"
    extra = "  ·  some hours have no matching price" if missing_price else ""
    return f"Latest day with usage  {fmt_day(day)}{extra}"


def _band(value: Decimal, vmin: Decimal | None, vmax: Decimal | None) -> str:
    if vmin is None or vmax is None or vmax <= vmin:
        return "mid"
    span = vmax - vmin
    t = (value - vmin) / span
    if t <= Decimal("0.333333"):
        return "low"
    if t >= Decimal("0.666667"):
        return "high"
    return "mid"


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


def _min_decimal(values: list[Decimal] | None) -> Decimal | None:
    nums = [item for item in (values or []) if item is not None]
    return min(nums) if nums else None


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
