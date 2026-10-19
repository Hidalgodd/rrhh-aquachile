"""Fecha y hora de Chile. El servidor puede estar en UTC; las reglas de RR. HH. no."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Santiago")


def ahora() -> datetime:
    return datetime.now(ZONA).replace(tzinfo=None)


def hoy() -> date:
    return ahora().date()
