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
PRICE_SCALE_MIN = Decimal("6")
PRICE_GREEN_UNTIL = Decimal("2")
PRICE_ORANGE_UNTIL = Decimal("4")
USAGE_SCALE_MIN = Decimal("2")
USAGE_GREEN_UNTIL = Decimal("1")
USAGE_ORANGE_UNTIL = Decimal("2")
SPENT_SCALE_MIN = Decimal("2")
SPENT_GREEN_UNTIL = Decimal("1")
SPENT_ORANGE_UNTIL = Decimal("2")

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
.trio { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.7rem; flex: 1; min-height: 0; }
/* Phones only. Tablets use the same side-by-side grid as computers. */
html[data-device="phone"] .pair,
html[data-device="phone"] .trio {
  grid-template-columns: 1fr;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 0.4rem;
  touch-action: pan-y;
}
html[data-device="phone"] .pair > .card,
html[data-device="phone"] .trio > .card {
  grid-area: 1 / 1;
  visibility: hidden;
  pointer-events: none;
}
html[data-device="phone"] .pair > .card.is-front,
html[data-device="phone"] .trio > .card.is-front,
html[data-device="phone"] .pair:not(:has(.is-front)) > .card:first-child,
html[data-device="phone"] .trio:not(:has(.is-front)) > .card:first-child {
  visibility: visible;
  pointer-events: auto;
}
.deck-nav { display: none; }
html[data-device="phone"] .deck-nav {
  grid-row: 2; grid-column: 1;
  display: flex; justify-content: center; align-items: center; gap: 0.75rem;
  z-index: 1;
}
.deck-btn, .deck-dot {
  appearance: none; background: transparent; color: var(--ink); cursor: pointer;
}
.deck-btn {
  width: 2.4rem; height: 2.4rem; border-radius: 999px;
  border: 1px solid var(--line); font-size: 1.4rem; line-height: 1;
}
.deck-dots { display: flex; gap: 0.45rem; align-items: center; }
.deck-dot {
  width: 0.7rem; height: 0.7rem; padding: 0; border-radius: 999px;
  border: 1px solid var(--muted);
}
.deck-dot.active { background: var(--ink); border-color: var(--ink); }
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
  background: linear-gradient(90deg,
    var(--low) 0%,
    var(--low) var(--g-green, 33.333%),
    var(--mid) var(--g-green, 33.333%),
    var(--mid) var(--g-orange, 66.667%),
    var(--high) var(--g-orange, 66.667%),
    var(--high) 100%);
  clip-path: inset(0 calc(100% - var(--w, 0%)) 0 0); }
.row .val { text-align: right; font-variant-numeric: tabular-nums;
  font-size: clamp(0.62rem, 1.5vh, 0.85rem); font-weight: 650; }
.empty-msg { color: var(--muted); margin: auto 0; }
.legend { flex: 0 0 auto; display: flex; align-items: center; gap: 0.55rem; color: var(--muted);
  font-size: 0.88rem; flex-wrap: wrap; }
.legend-bar { width: 8rem; height: 0.5rem; border-radius: 999px;
  background: linear-gradient(90deg,
    var(--low) 0%,
    var(--low) var(--g-green, 33.333%),
    var(--mid) var(--g-green, 33.333%),
    var(--mid) var(--g-orange, 66.667%),
    var(--high) var(--g-orange, 66.667%),
    var(--high) 100%); }
.panel-prices .legend-bar { width: 12rem; }
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

# Runs in <head> so the phone layout is set before the charts paint.
DETECT_JS = """
(() => {
  const ua = navigator.userAgent || "";
  const touch = (navigator.maxTouchPoints || 0) > 0;
  const shortSide = Math.min(screen.width || 0, screen.height || 0);
  const iPad = /iPad/.test(ua)
    || ((/Macintosh/.test(ua) || navigator.platform === "MacIntel") && touch && shortSide >= 700);
  const androidTablet = /Android/i.test(ua) && !/Mobile/i.test(ua);
  const tabletHint = /Tablet|PlayBook|Silk/i.test(ua);
  let device = "desktop";
  if (iPad || androidTablet || tabletHint) device = "tablet";
  else if (
    /iPhone|iPod|Windows Phone|IEMobile|BlackBerry|Opera Mini/i.test(ua)
    || (/Android/i.test(ua) && /Mobile/i.test(ua))
    || (navigator.userAgentData && navigator.userAgentData.mobile === true && shortSide > 0 && shortSide < 700)
    || (touch && shortSide > 0 && shortSide < 700)
  ) device = "phone";
  else if (touch && shortSide >= 700 && shortSide < 1200) device = "tablet";
  document.documentElement.dataset.device = device;
})();
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

  if (document.documentElement.dataset.device === "phone") {{
    document.querySelectorAll(".pair, .trio").forEach((deck) => {{
      const cards = Array.from(deck.children).filter((node) => node.classList.contains("card"));
      if (cards.length < 2) return;
      const nav = document.createElement("div");
      nav.className = "deck-nav";
      const prev = document.createElement("button");
      prev.type = "button";
      prev.className = "deck-btn";
      prev.setAttribute("aria-label", "Previous chart");
      prev.textContent = "‹";
      const dots = document.createElement("div");
      dots.className = "deck-dots";
      const next = document.createElement("button");
      next.type = "button";
      next.className = "deck-btn";
      next.setAttribute("aria-label", "Next chart");
      next.textContent = "›";
      const dotButtons = cards.map((card, i) => {{
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "deck-dot";
        const title = card.querySelector(".card-title");
        dot.setAttribute("aria-label", title ? title.textContent : ("Chart " + (i + 1)));
        dots.appendChild(dot);
        return dot;
      }});
      nav.append(prev, dots, next);
      deck.appendChild(nav);
      let index = 0;
      let startX = 0;
      let startY = 0;
      let tracking = false;
      const show = (nextIndex) => {{
        index = (nextIndex + cards.length) % cards.length;
        cards.forEach((card, i) => card.classList.toggle("is-front", i === index));
        dotButtons.forEach((dot, i) => {{
          dot.classList.toggle("active", i === index);
          dot.setAttribute("aria-current", i === index ? "true" : "false");
        }});
      }};
      prev.addEventListener("click", () => show(index - 1));
      next.addEventListener("click", () => show(index + 1));
      dotButtons.forEach((dot, i) => dot.addEventListener("click", () => show(i)));
      deck.addEventListener("pointerdown", (event) => {{
        if (event.target.closest(".deck-nav")) return;
        tracking = true;
        startX = event.clientX;
        startY = event.clientY;
      }});
      deck.addEventListener("pointerup", (event) => {{
        if (!tracking) return;
        tracking = false;
        const dx = event.clientX - startX;
        const dy = event.clientY - startY;
        if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy)) return;
        show(index + (dx < 0 ? 1 : -1));
      }});
      deck.addEventListener("pointercancel", () => {{ tracking = false; }});
      show(0);
    }});
  }}
}})();
"""


app, rt = fast_app(
    title="The Family Dashboard",
    pico=False,
    hdrs=(Style(CSS), Script(DETECT_JS)),
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
    price_scale = _value_scale(price_values, PRICE_SCALE_MIN)

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
                _price_legend(price_scale),
                Div(
                    _price_card("Today", today, today_hours, price_scale, now),
                    _price_card("Tomorrow", tomorrow, tomorrow_hours, price_scale, None),
                    cls="pair",
                ),
                cls="panel panel-prices",
                style=_gradient_style(
                    price_scale, PRICE_GREEN_UNTIL, PRICE_ORANGE_UNTIL
                ),
            ),
            Div(
                _hero(
                    [
                        (fmt_kwh(usage_total) if usage_hours else "—", "kWh"),
                        (fmt_kr(cost_total) if cost_total is not None else "—", "kr"),
                    ],
                    _usage_caption(usage_day, latest_usage, missing_price),
                ),
                Div(
                    _usage_card("Usage", usage_hours, "usage"),
                    _usage_card("Price", usage_hours, "price"),
                    _usage_card("Spent", usage_hours, "cost"),
                    cls="trio",
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


def _price_legend(scale: Decimal):
    return Div(
        Span("0"),
        Span(cls="legend-bar"),
        Span(f"{fmt_kr(scale)} kr"),
        Span("·  0–2 green  ·  2–4 orange  ·  4+ red"),
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
        scale = _value_scale(values, SPENT_SCALE_MIN)
        green, orange = SPENT_GREEN_UNTIL, SPENT_ORANGE_UNTIL
        format_value = fmt_kr
        caption = (
            f"0–{fmt_kr(scale)} kr  ·  0–1 green  ·  1–2 orange  ·  2+ red"
        )
    elif kind == "price":
        values = [item.price_incl_vat for item in hours]
        scale = _value_scale(values, PRICE_SCALE_MIN)
        green, orange = PRICE_GREEN_UNTIL, PRICE_ORANGE_UNTIL
        format_value = fmt_kr
        caption = (
            f"0–{fmt_kr(scale)} kr/kWh  ·  0–2 green  ·  2–4 orange  ·  4+ red"
        )
    else:
        values = [item.usage_kwh for item in hours]
        scale = _value_scale(values, USAGE_SCALE_MIN)
        green, orange = USAGE_GREEN_UNTIL, USAGE_ORANGE_UNTIL
        format_value = fmt_kwh
        caption = (
            f"0–{fmt_kwh(scale)} kWh  ·  0–1 green  ·  1–2 orange  ·  2+ red"
        )
    rows = [
        _hour_row(
            hour=item.local_hour,
            value=value,
            shown=format_value(value) if value is not None else "—",
            vmax=scale,
            is_now=False,
        )
        for item, value in zip(hours, values)
    ]
    return Div(
        Div(title, cls="card-title"),
        P(caption, cls="when"),
        Div(*rows, cls="chart"),
        cls="card",
        style=_gradient_style(scale, green, orange),
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
    if value <= 0:
        return 0
    pct = int((value / vmax * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))
    return min(max(pct, 4), 100)


def _value_scale(values: list[Decimal] | None, minimum: Decimal) -> Decimal:
    vmax = _max_decimal(values)
    if vmax is None or vmax <= minimum:
        return minimum
    return vmax


def _stop_pct(amount: Decimal, scale: Decimal) -> str:
    if scale <= 0:
        return "0"
    pct = (amount / scale * Decimal("100")).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    if pct < 0:
        pct = Decimal("0")
    if pct > 100:
        pct = Decimal("100")
    return format(pct, "f")


def _gradient_style(
    scale: Decimal, green_until: Decimal, orange_until: Decimal
) -> str:
    green = _stop_pct(green_until, scale)
    orange = _stop_pct(orange_until, scale)
    return f"--g-green:{green}%;--g-orange:{orange}%"


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
