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

Header: **The Family Dashboard**. Two tabs, rotated every five minutes (the page also reloads so the numbers stay current):

1. **Current prices** — today’s and tomorrow’s total inkl. moms, as side-by-side 24-hour bar charts. Bars are green / orange / red from cheap to expensive. The current hour is marked, and that hour’s price is shown large above the charts.
2. **Power usage** — the latest date that has hourly usage (ElOverblik is usually a day behind). One chart is kWh per hour, the other is that hour’s usage times that hour’s stored price. Totals for the day sit above the charts.

## Requirements

- Python 3
- PostgreSQL with schemas `eloverblick` and `elprisenligenu` already populated
- `PRISKLASSE` set to `DK1` or `DK2` (must match the stored prices)

```bash
cp .env.example .env
# fill in Postgres settings
python3 -m web
```

Open http://127.0.0.1:8089

Unraid Docker Compose deploy is in [deploy.md](deploy.md).

## Status

Version `0.0.1`. See [CHANGELOG.md](CHANGELOG.md).
