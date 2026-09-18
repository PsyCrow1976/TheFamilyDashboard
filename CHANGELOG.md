# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-09-18

### Added

- FastHTML dashboard that reads hourly electricity prices and usage from an existing PostgreSQL database.
- Prices tab: today and tomorrow total inkl. moms as green / orange / red hour charts, with the current hour marked and shown large.
- Usage tab: latest stored usage day, kWh per hour, kroner per hour (usage × that hour’s price), and day totals.
- Tabs rotate and the page reloads every five minutes.
- Docker Compose deploy against the shared `home` network, documented in `deploy.md`.
