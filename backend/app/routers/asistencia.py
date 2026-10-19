import re
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import DbSession, empleado_actual, exigir_acceso_a, get_current_user
from app.models.empleado import Empleado
from app.models.rrhh import Asistencia
from app.models.usuario import Usuario
from app.tiempo import ahora, hoy

router = APIRouter(prefix="/api/asistencia", tags=["Asistencia"])


def _hhmm(t) -> str | None:
    return t.strftime("%H:%M") if t else None


def _fila(a: Asistencia) -> dict:
    horas = None
    if a.hora_entrada and a.hora_salida:
        ini = datetime.combine(a.fecha, a.hora_entrada)
        fin = datetime.combine(a.fecha, a.hora_salida)
        horas = round((fin - ini).total_seconds() / 3600, 1)
    return {
        "fecha": a.fecha,
        "entrada": _hhmm(a.hora_entrada),
        "salida": _hhmm(a.hora_salida),
        "horas": horas,
    }


def _mes(mes: str | None) -> tuple[date, date]:
    if mes is None:
        d = hoy()
    else:
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", mes):
            raise HTTPException(status_code=422, detail="El mes debe tener el formato AAAA-MM")
        d = date(int(mes[:4]), int(mes[5:]), 1)
    inicio = d.replace(day=1)
    fin = date(inicio.year + (inicio.month == 12), inicio.month % 12 + 1, 1)
    return inicio, fin


def _listar(db: Session, id_empleado: int, mes: str | None) -> dict:
    inicio, fin = _mes(mes)
    filas = (
        db.query(Asistencia)
        .filter(
            Asistencia.id_empleado == id_empleado,
            Asistencia.fecha >= inicio,
            Asistencia.fecha < fin,
        )
        .order_by(Asistencia.fecha.desc())
        .all()
    )
    hoy_fila = (
        db.query(Asistencia)
        .filter(Asistencia.id_empleado == id_empleado, Asistencia.fecha == hoy())
        .first()
    )
    return {
        "mes": inicio.strftime("%Y-%m"),
        "hoy": _fila(hoy_fila) if hoy_fila else {"fecha": hoy(), "entrada": None, "salida": None, "horas": None},
        "registros": [_fila(a) for a in filas],
    }


@router.post("/marcar")
def marcar(empleado: Annotated[Empleado, Depends(empleado_actual)], db: DbSession):
    """Primera marca del día = entrada; la segunda = salida."""
    ahora_ = ahora()
    fila = (
        db.query(Asistencia)
        .filter(Asistencia.id_empleado == empleado.id_empleado, Asistencia.fecha == ahora_.date())
        .first()
    )
    if fila is None:
        fila = Asistencia(
            id_empleado=empleado.id_empleado,
            fecha=ahora_.date(),
            hora_entrada=ahora_.time().replace(microsecond=0),
        )
        db.add(fila)
    elif fila.hora_salida is None:
        fila.hora_salida = ahora_.time().replace(microsecond=0)
    else:
        raise HTTPException(status_code=409, detail="Ya marcaste entrada y salida hoy")
    db.commit()
    db.refresh(fila)
    return _fila(fila)


@router.get("/mia")
def mia(
    empleado: Annotated[Empleado, Depends(empleado_actual)],
    db: DbSession,
    mes: Annotated[str | None, Query()] = None,
):
    return _listar(db, empleado.id_empleado, mes)


@router.get("/de/{id_empleado}")
def de_empleado(
    id_empleado: int,
    usuario: Annotated[Usuario, Depends(get_current_user)],
    db: DbSession,
    mes: Annotated[str | None, Query()] = None,
):
    exigir_acceso_a(usuario, id_empleado)
    return _listar(db, id_empleado, mes)
