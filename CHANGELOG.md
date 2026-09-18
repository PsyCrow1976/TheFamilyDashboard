# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.5] - 2026-09-18

### Changed

- Hour-bar colors use fixed thresholds instead of each day’s min/max. Current prices: 0–2 kr green, 2–4 kr orange, 4+ kr red, on a 0–6 kr/kWh width that grows if an hour is above 6.
- Power usage kWh: 0–1 green, 1–2 orange, 2+ red, on a 0–2 kWh width that grows if an hour is above 2.
- Spent kr: 0–1 green, 1–2 orange, 2+ red, on a 0–2 kr width that grows if an hour is above 2.

### Added

- A middle hourly price chart on the power usage tab for the day being viewed, using the same 0–2 / 2–4 / 4+ kr stops as Current prices.

## [0.0.4] - 2026-09-18

### Changed

- Hour rows stretch to fill leftover browser height, so the bar thickness grows with the window the same way bar length follows the value.

### Added

- Previous / next day buttons under the power usage charts, limited to days that have stored hourly usage.

## [0.0.3] - 2026-09-18

### Changed

- Each hour line uses a green → orange → red gradient instead of a solid color. Short bars stay in the green; longer bars continue through orange into red.

## [0.0.2] - 2026-09-18

### Changed

- Hour charts are horizontal lines: time (`00-01` … `23-24`) on the left, the bar in the middle, and the hour’s value on the right. Same layout for prices and usage.

## [0.0.1] - 2026-09-18

### Added

- FastHTML dashboard that reads hourly electricity prices and usage from an existing PostgreSQL database.
- Prices tab: today and tomorrow total inkl. moms as green / orange / red hour charts, with the current hour marked and shown large.
- Usage tab: latest stored usage day, kWh per hour, kroner per hour (usage × that hour’s price), and day totals.
- Tabs rotate and the page reloads every five minutes.
- Docker Compose deploy against the shared `home` network, documented in `deploy.md`.
