from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.rrhh import Permiso

LARGO_BLOQUE = {"7x7": 7, "14x14": 14}


def trabaja(regimen: str, fecha_ancla: date, fecha: date) -> bool:
    """¿El grupo está en su bloque de trabajo ese día?"""
    n = LARGO_BLOQUE[regimen]
    return (fecha - fecha_ancla).days % (2 * n) < n


def ventana(hoy: date, dias: int = 14) -> list[date]:
    """Dos semanas que parten el lunes de la semana actual."""
    lunes = hoy - timedelta(days=hoy.weekday())
    return [lunes + timedelta(i) for i in range(dias)]


def bloques(estados: list[str | None]) -> list[dict]:
    """Une días consecutivos con el mismo estado: [{tipo, inicio, fin}] (índices)."""
    out: list[dict] = []
    for i, e in enumerate(estados):
        if e is None:
            continue
        if out and out[-1]["tipo"] == e and out[-1]["fin"] == i - 1:
            out[-1]["fin"] = i
        else:
            out.append({"tipo": e, "inicio": i, "fin": i})
    return out


def ausencias(db: Session, ids: list[int], desde: date, hasta: date) -> dict[int, list[Permiso]]:
    """Permisos aprobados que tocan el rango, por empleado."""
    out: dict[int, list[Permiso]] = defaultdict(list)
    if not ids:
        return out
    filas = (
        db.query(Permiso)
        .filter(
            Permiso.id_empleado.in_(ids),
            Permiso.estado == "aprobado",
            Permiso.fecha_inicio <= hasta,
            Permiso.fecha_termino >= desde,
        )
        .all()
    )
    for p in filas:
        out[p.id_empleado].append(p)
    return out


ETIQUETA_AUSENCIA = {"vacaciones": "vacaciones", "licencia medica": "licencia", "administrativo": "permiso"}


def tipo_ausencia(permisos: list[Permiso], dia: date) -> str | None:
    for p in permisos:
        if p.fecha_inicio <= dia <= p.fecha_termino:
            return ETIQUETA_AUSENCIA[p.tipo]
    return None
