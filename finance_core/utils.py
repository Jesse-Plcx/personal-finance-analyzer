from __future__ import annotations

import re
from datetime import datetime


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", "").strip()


def parse_amount(value: object) -> float:
    if value is None:
        return 0.0
    text = str(value).replace(",", "").replace("¥", "").replace(" ", "").strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_date(value: object) -> tuple[int, int, int, str] | None:
    if value is None:
        return None
    text = str(value).replace("\n", " ").strip()
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    time_match = re.search(r"(\d{2}:\d{2}:\d{2})", text)
    full_dt = f"{year:04d}-{month:02d}-{day:02d} {time_match.group(1) if time_match else '00:00:00'}"
    return year, month, day, full_dt


def utc_now_text() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
