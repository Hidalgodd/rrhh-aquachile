from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_rrhh
from app.models.empleado import Area, Cargo, Empleado
from app.models.postulante import Postulante
from app.tiempo import hoy

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_rrhh)],
)
DbSession = Annotated[Session, Depends(get_db)]

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def _fin_de_mes(anio: int, mes: int) -> date:
    return date(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1)


def _meses(hoy_: date, n: int = 12) -> list[tuple[int, int]]:
    """Los últimos n meses, terminando en el actual."""
    out, a, m = [], hoy_.year, hoy_.month
    for _ in range(n):
        out.append((a, m))
        m -= 1
        if m == 0:
            a, m = a - 1, 12
    return out[::-1]


def _presente(ingreso: date, salida: date | None, estado: str, corte: date) -> bool:
    if estado == "inactivo" and salida is None:
        return False  # sin fecha de salida no se sabe cuándo dejó de contar
    return ingreso <= corte and (salida is None or salida > corte)


@router.get("/resumen")
def resumen(db: DbSession):
    hoy_ = hoy()
    por_estado = dict(
        db.query(Empleado.estado, func.count(Empleado.id_empleado))
        .group_by(Empleado.estado)
        .all()
    )
    inicio_mes = hoy_.replace(day=1)
    nuevos_mes = (
        db.query(func.count(Empleado.id_empleado))
        .filter(Empleado.fecha_ingreso >= inicio_mes, Empleado.estado != "inactivo")
        .scalar()
    )
    postulantes_pendientes = (
        db.query(func.count(Postulante.id_postulante))
        .filter(Postulante.estado.in_(["recibido", "en revisión"]))
        .scalar()
    )

    # Dotación (activos + en licencia) de cada área, mes a mes: quien ya había
    # ingresado a fin de mes y todavía no se había ido.
    filas = (
        db.query(Area.nombre, Empleado.fecha_ingreso, Empleado.fecha_salida, Empleado.estado)
        .join(Cargo, Cargo.id_area == Area.id_area)
        .join(Empleado, Empleado.id_cargo == Cargo.id_cargo)
        .all()
    )
    areas = sorted({f[0] for f in filas})
    meses = _meses(hoy_)
    serie = {a: [0] * len(meses) for a in areas}
    for area, ingreso, salida, estado in filas:
        for i, (a, m) in enumerate(meses):
            if _presente(ingreso, salida, estado, min(_fin_de_mes(a, m), hoy_)):
                serie[area][i] += 1

    actual = {a: serie[a][-1] for a in areas}
    por_area = sorted(
        ({"area": a, "total": t} for a, t in actual.items() if t > 0),
        key=lambda x: -x["total"],
    )
    dotacion = sum(actual.values())
    corte_anio = hoy_ - timedelta(days=365)
    hace_un_anio = sum(1 for _, i, s_, e in filas if _presente(i, s_, e, corte_anio))
    return {
        "activos": por_estado.get("activo", 0),
        "licencia": por_estado.get("licencia", 0),
        "inactivos": por_estado.get("inactivo", 0),
        "dotacion": dotacion,
        "dotacion_hace_un_anio": hace_un_anio,
        "nuevos_mes": nuevos_mes or 0,
        "postulantes_pendientes": postulantes_pendientes or 0,
        "por_area": por_area,
        "serie": {
            "meses": [MESES[m - 1] for _, m in meses],
            "areas": [{"area": a, "valores": serie[a]} for a in areas if actual[a] > 0],
        },
    }
