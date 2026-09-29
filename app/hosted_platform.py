"""Host selection and the Neon-friendly worker schedule.

The same app runs on Vercel Hobby or Cloudflare Workers. Storage is a
separate env var. This module does not import the quoting engine.
"""

from __future__ import annotations

import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

NEON_FREE_CU_HOURS = 100
NEON_SUSPEND_AFTER_S = 300
DEFAULT_ACTIVE_HOURS = "Mon-Fri 06:00-18:00"
DEFAULT_TIMEZONE = "America/Chicago"

_DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def platform_name() -> str:
    raw = (os.getenv("HOSTED_PLATFORM") or "vercel").strip().lower()
    if raw == "cloudflare":
        return "cloudflare"
    return "vercel"


def suggested_storage() -> str:
    """Docs and the platform endpoint. An explicit provider still wins at runtime."""
    explicit = (os.getenv("HOSTED_BLOB_PROVIDER") or "").strip().lower()
    if explicit:
        return explicit
    if platform_name() == "cloudflare":
        return "r2"
    return "vercel"


def always_on_cu_hours(cu: float = 0.25, days: float = 30.4) -> float:
    """24/7 compute. Neon free is 100 CU-hours; this is over the cap."""
    return 24 * days * cu


def busy_workweek_cu_hours(cu: float = 0.25, days: float = 30.4) -> float:
    """Mon-Fri 06:00-18:00 with the database awake the whole window."""
    weekdays = 5 * (days / 7)
    return weekdays * 12 * cu


def empty_workweek_cu_hours(
    backoff_max_s: float = 900,
    cu: float = 0.25,
    days: float = 30.4,
    suspend_after_s: float = NEON_SUSPEND_AFTER_S,
) -> float:
    """Empty workweek. Each probe keeps compute awake until Neon suspends."""
    weekdays = 5 * (days / 7)
    probes_per_day = (12 * 3600) / backoff_max_s
    awake_hours_per_probe = suspend_after_s / 3600
    return weekdays * probes_per_day * awake_hours_per_probe * cu


def parse_active_hours(spec: str | None = None) -> tuple[frozenset[int], time, time]:
    raw = (spec if spec is not None else os.getenv("HOSTED_WORKER_ACTIVE_HOURS") or DEFAULT_ACTIVE_HOURS).strip()
    day_part, time_part = raw.split()
    if "-" in day_part and "," not in day_part:
        start_name, end_name = day_part.split("-", 1)
        start_i = _DAYS[start_name[:3].lower()]
        end_i = _DAYS[end_name[:3].lower()]
        if start_i <= end_i:
            days = frozenset(range(start_i, end_i + 1))
        else:
            days = frozenset(list(range(start_i, 7)) + list(range(0, end_i + 1)))
    else:
        days = frozenset(_DAYS[piece[:3].lower()] for piece in day_part.split(",") if piece)
    start_s, end_s = time_part.split("-")
    start_h, start_m = (int(part) for part in start_s.split(":"))
    end_h, end_m = (int(part) for part in end_s.split(":"))
    return days, time(start_h, start_m), time(end_h, end_m)


def worker_zone() -> ZoneInfo:
    name = (os.getenv("HOSTED_WORKER_TIMEZONE") or DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
    return ZoneInfo(name)


def in_active_hours(moment: datetime, *, spec: str | None = None, zone: ZoneInfo | None = None) -> bool:
    """Start is inclusive. End is exclusive. Days are the shop's local weekday."""
    local = moment.astimezone(zone or worker_zone())
    days, start, end = parse_active_hours(spec)
    if local.weekday() not in days:
        return False
    clock = local.timetz().replace(tzinfo=None)
    return start <= clock < end


def seconds_until_active(moment: datetime, *, spec: str | None = None, zone: ZoneInfo | None = None) -> float:
    if in_active_hours(moment, spec=spec, zone=zone):
        return 0.0
    zone = zone or worker_zone()
    local = moment.astimezone(zone)
    days, start, _end = parse_active_hours(spec)
    for offset in range(0, 8):
        day = local.date() + timedelta(days=offset)
        probe = datetime.combine(day, start, tzinfo=zone)
        if probe.weekday() not in days or probe <= local:
            continue
        return (probe - local).total_seconds()
    return 0.0


def empty_backoff(streak: int) -> float:
    """Seconds to wait after an empty queue. The default cap is 15 minutes.

    Neon suspends after 5 minutes idle. A cap at or under 300 seconds would
    reset that timer and keep the free compute awake.
    """
    base = float(os.getenv("HOSTED_WORKER_EMPTY_BACKOFF_S") or "15")
    cap = float(os.getenv("HOSTED_WORKER_EMPTY_BACKOFF_MAX_S") or "900")
    power = max(0, int(streak) - 1)
    return min(cap, base * (2**power))


def fast_poll_s() -> float:
    return max(1.0, float(os.getenv("HOSTED_WORKER_POLL_S") or "5"))


def offhours_poll_s() -> float:
    return float(os.getenv("HOSTED_WORKER_OFFHOURS_POLL_S") or "0")


def decide_poll(moment: datetime, *, empty_streak: int, purged_day: object | None) -> dict[str, object]:
    """One worker tick. contact False means do not call the API."""
    active = in_active_hours(moment)
    fast = fast_poll_s()
    if not active:
        off = offhours_poll_s()
        if off <= 0:
            return {
                "contact": False,
                "purge": False,
                "sleep_before": seconds_until_active(moment),
                "fast_s": fast,
            }
        return {"contact": True, "purge": False, "sleep_before": off, "fast_s": fast}
    local_day = moment.astimezone(worker_zone()).date()
    return {
        "contact": True,
        "purge": purged_day != local_day,
        "sleep_before": empty_backoff(empty_streak) if empty_streak > 0 else 0.0,
        "fast_s": fast,
    }
