# The Family Dashboard

FastHTML dashboard for a household electricity wall display. It reads hourly **prices** and **usage** that other apps have already stored in PostgreSQL. It does not call ElOverblik or the price APIs itself.

- Usage is stored by [eloverblick](https://github.com/PsyCrow1976/eloverblick)
- Prices are stored by [elprisenligenu](https://github.com/PsyCrow1976/elprisenligenu)

Hourly spot prices in that database come from the open [Elpris API](https://www.elprisenligenu.dk/elpris-api) at [Elprisen lige nu.dk](https://www.elprisenligenu.dk).

<p>
  <a href="https://www.elprisenligenu.dk">
    <img
      src="https://i.bnfcl.io/hva-koster-strommen/elpriser-leveret-af-elprisenligenu_LJNbbujZAX.png"
      alt="Elpriser leveret af Elprisen lige nu.dk"
      width="200"
      height="45">
  </a>
</p>

## What it shows

Header: **The Family Dashboard**. Three tabs, rotated every five minutes (the page also reloads so the numbers stay current):

1. **Current prices** — today’s and tomorrow’s total inkl. moms, as side-by-side 24-hour charts on a computer or tablet. On a phone the two charts share one space and only one is visible; swipe sideways or use the arrows and dots to switch. Each hour is a horizontal line (`00-01` … `23-24`) with the value on the right. The bar is a green → orange → red gradient with stops at 2 kr and 4 kr. Width is 0–6 kr/kWh unless an hour is higher. The current hour is marked, and that hour’s price is shown large above the charts.
2. **Power usage** — the latest date that has hourly usage (ElOverblik is usually a day behind). Three charts: kWh per hour (0–1 / 1–2 / 2+ kWh), that day’s hourly price (same 0–2 / 2–4 / 4+ kr stops as Current prices), and kroner spent per hour (0–1 / 1–2 / 2+ kr). On a computer or tablet they sit side by side. On a phone they stack in the same space, one visible at a time. Totals for the day sit above the charts. Previous / next day buttons at the bottom step through stored usage days.
3. **Calendar** — today and tomorrow from one Google calendar. Set `GOOGLE_CALENDAR_ICS_URL` to that calendar’s secret iCal address (Google Calendar → Settings → the calendar → Integrate calendar). The app downloads the feed about every five minutes and keeps the latest copy in memory. Events are not written to PostgreSQL. On a phone, today and tomorrow share one space the same way the price charts do.

## Requirements

- Python 3
- PostgreSQL with schemas `eloverblick` and `elprisenligenu` already populated
- `PRISKLASSE` set to `DK1` or `DK2` (must match the stored prices)
- Optional: `GOOGLE_CALENDAR_ICS_URL`, the secret iCal address of one Google calendar

```bash
cp .env.example .env
# fill in Postgres settings
python3 -m web
```

Open http://127.0.0.1:8089

Unraid Docker Compose deploy is in [deploy.md](deploy.md).

## Status

Version `0.0.8`. See [CHANGELOG.md](CHANGELOG.md).
