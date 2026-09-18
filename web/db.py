"""Read electricity prices and usage from the shared PostgreSQL database."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass
class PriceHour:
    local_date: date
    local_hour: int
    total_incl_vat: Decimal
    spot_dkk_kwh: Decimal


@dataclass
class UsageHour:
    local_date: date
    local_hour: int
    usage_kwh: Decimal
    price_incl_vat: Decimal | None
    cost_dkk: Decimal | None


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        if default is not None:
            return default
        raise RuntimeError(f"{name} must be set.")
    return value


def price_area() -> str:
    return _env("PRISKLASSE", "DK2").upper()


def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=_env("POSTGRES_HOST"),
        port=int(_env("POSTGRES_PORT", "5432")),
        user=_env("POSTGRES_USER"),
        password=_env("POSTGRES_PASSWORD"),
        dbname=_env("POSTGRES_DB", "home"),
        row_factory=dict_row,
        connect_timeout=10,
    )


def any_meter_id() -> str | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT metering_point_id
            FROM eloverblick.metering_points
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()
    return row["metering_point_id"] if row else None


def list_price_hours(day: date, area: str | None = None) -> list[PriceHour]:
    area = area or price_area()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT local_date, local_hour, total_incl_vat, spot_dkk_kwh
            FROM elprisenligenu.hours
            WHERE price_area = %s AND local_date = %s
            ORDER BY period_start
            """,
            (area, day),
        ).fetchall()
    return [_price_hour(row) for row in rows]


def latest_usage_date(metering_point_id: str | None = None) -> date | None:
    meter = metering_point_id or any_meter_id()
    if meter is None:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT MAX(local_date) AS latest
            FROM eloverblick.hours
            WHERE metering_point_id = %s
            """,
            (meter,),
        ).fetchone()
    return row["latest"] if row else None


def list_usage_hours(
    day: date,
    metering_point_id: str | None = None,
    area: str | None = None,
) -> list[UsageHour]:
    meter = metering_point_id or any_meter_id()
    if meter is None:
        return []
    area = area or price_area()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                h.local_date,
                h.local_hour,
                h.usage_kwh,
                p.total_incl_vat AS price_incl_vat,
                CASE
                    WHEN p.total_incl_vat IS NULL THEN NULL
                    ELSE h.usage_kwh * p.total_incl_vat
                END AS cost_dkk
            FROM eloverblick.hours h
            LEFT JOIN elprisenligenu.hours p
              ON p.price_area = %s
             AND p.local_date = h.local_date
             AND p.local_hour = h.local_hour
            WHERE h.metering_point_id = %s
              AND h.local_date = %s
            ORDER BY h.period_start
            """,
            (area, meter, day),
        ).fetchall()
    return [_usage_hour(row) for row in rows]


def _price_hour(row: dict[str, Any]) -> PriceHour:
    return PriceHour(
        local_date=row["local_date"],
        local_hour=int(row["local_hour"]),
        total_incl_vat=row["total_incl_vat"],
        spot_dkk_kwh=row["spot_dkk_kwh"],
    )


def _usage_hour(row: dict[str, Any]) -> UsageHour:
    return UsageHour(
        local_date=row["local_date"],
        local_hour=int(row["local_hour"]),
        usage_kwh=row["usage_kwh"],
        price_incl_vat=row["price_incl_vat"],
        cost_dkk=row["cost_dkk"],
    )
