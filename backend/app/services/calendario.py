"""Días hábiles de Chile (lunes a viernes sin feriados).

Los feriados fijos se repiten todos los años. Los que se corren de fecha
(Semana Santa, San Pedro y San Pablo, Encuentro de Dos Mundos, etc.) se
declaran año por año: hay que revisar esta lista cada diciembre.
"""
from datetime import date, timedelta

FERIADOS_FIJOS = {
    (1, 1), (5, 1), (5, 21), (7, 16), (8, 15), (9, 18), (9, 19), (11, 1), (12, 8), (12, 25),
}

FERIADOS_POR_ANIO = {
    date(2026, 4, 3), date(2026, 4, 4),     # Semana Santa
    date(2026, 6, 21), date(2026, 6, 29),   # Pueblos Indígenas, San Pedro y San Pablo
    date(2026, 10, 12), date(2026, 10, 31),  # Encuentro de Dos Mundos, Iglesias Evangélicas
}


def es_feriado(d: date) -> bool:
    return (d.month, d.day) in FERIADOS_FIJOS or d in FERIADOS_POR_ANIO


def es_habil(d: date) -> bool:
    return d.weekday() < 5 and not es_feriado(d)


def dias_habiles(desde: date, hasta: date) -> int:
    if hasta < desde:
        return 0
    return sum(1 for i in range((hasta - desde).days + 1) if es_habil(desde + timedelta(i)))


def lunes_de(d: date) -> date:
    return d - timedelta(days=d.weekday())
