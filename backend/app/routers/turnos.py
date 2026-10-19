from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_rrhh
from app.models.empleado import Area, Cargo, Empleado
from app.models.rrhh import Asistencia, Centro, Turno
from app.services.turnos import ausencias, bloques, tipo_ausencia, trabaja, ventana
from app.tiempo import hoy

router = APIRouter(
    prefix="/api",
    tags=["Centros y turnos"],
    dependencies=[Depends(require_rrhh)],
)
DbSession = Annotated[Session, Depends(get_db)]

DIAS = ["L", "M", "M", "J", "V", "S", "D"]


def _personas_por_turno(db: Session) -> dict[int, int]:
    filas = (
        db.query(Empleado.id_turno, func.count(Empleado.id_empleado))
        .filter(Empleado.id_turno.isnot(None), Empleado.estado != "inactivo")
        .group_by(Empleado.id_turno)
        .all()
    )
    return {t: n for t, n in filas}


@router.get("/centros")
def listar_centros(db: DbSession):
    centros = db.query(Centro).order_by(Centro.nombre).all()
    turnos = db.query(Turno).order_by(Turno.grupo, Turno.regimen).all()
    personas = _personas_por_turno(db)
    return [
        {
            "id_centro": c.id_centro,
            "nombre": c.nombre,
            "tipo": c.tipo,
            "turnos": [
                {
                    "id_turno": t.id_turno,
                    "grupo": t.grupo,
                    "regimen": t.regimen,
                    "personas": personas.get(t.id_turno, 0),
                }
                for t in turnos
                if t.id_centro == c.id_centro
            ],
        }
        for c in centros
    ]


@router.get("/turnos/grilla")
def grilla(
    db: DbSession,
    id_centro: Annotated[int | None, Query(gt=0)] = None,
    grupo: Annotated[Literal["A", "B"], Query()] = "A",
    regimen: Annotated[Literal["7x7", "14x14"], Query()] = "7x7",
):
    """Dos semanas de un grupo: quién trabaja, quién está ausente y quién ya marcó hoy."""
    if id_centro is None:
        primero = db.query(Centro).order_by(Centro.nombre).first()
        if primero is None:
            raise HTTPException(status_code=404, detail="Aún no hay centros creados")
        id_centro = primero.id_centro
    centro = db.get(Centro, id_centro)
    if centro is None:
        raise HTTPException(status_code=404, detail="Centro no encontrado")

    hoy_ = hoy()
    dias = ventana(hoy_)
    base = {
        "centro": {"id_centro": centro.id_centro, "nombre": centro.nombre},
        "grupo": grupo,
        "regimen": regimen,
        "dias": [d.isoformat() for d in dias],
        "letras": [DIAS[d.weekday()] for d in dias],
        "hoy_idx": dias.index(hoy_),
        "turno": None,
        "trabaja_hoy": False,
        "esperados": 0,
        "marcaron": 0,
        "personas": [],
    }
    turno = (
        db.query(Turno)
        .filter(Turno.id_centro == id_centro, Turno.grupo == grupo, Turno.regimen == regimen)
        .first()
    )
    if turno is None:
        return base

    empleados = (
        db.query(Empleado)
        .filter(Empleado.id_turno == turno.id_turno, Empleado.estado != "inactivo")
        .order_by(Empleado.apellidos, Empleado.nombres)
        .all()
    )
    ids = [e.id_empleado for e in empleados]
    ause = ausencias(db, ids, dias[0], dias[-1])
    marcas = {
        a.id_empleado: a
        for a in db.query(Asistencia).filter(
            Asistencia.fecha == hoy_, Asistencia.id_empleado.in_(ids or [0])
        )
    }

    trabaja_hoy = trabaja(turno.regimen, turno.fecha_ancla, hoy_)
    personas, esperados, marcaron = [], 0, 0
    for e in empleados:
        estados: list[str | None] = []
        for d in dias:
            if not trabaja(turno.regimen, turno.fecha_ancla, d):
                estados.append(None)
                continue
            aus = tipo_ausencia(ause[e.id_empleado], d)
            if aus is None and e.estado == "licencia" and d >= hoy_:
                aus = "licencia"
            estados.append(aus or "turno")

        estado_hoy = estados[base["hoy_idx"]]
        if estado_hoy is None:
            hoy_txt = "Descanso"
        elif estado_hoy != "turno":
            hoy_txt = estado_hoy.capitalize()
        else:
            esperados += 1
            marca = marcas.get(e.id_empleado)
            if marca and marca.hora_entrada:
                marcaron += 1
                hoy_txt = marca.hora_entrada.strftime("%H:%M")
            else:
                hoy_txt = "Sin marcar"
        personas.append(
            {
                "id_empleado": e.id_empleado,
                "nombre": f"{e.nombres.split()[0]} {e.apellidos.split()[0]}",
                "iniciales": (e.nombres[0] + e.apellidos[0]).upper(),
                "bloques": bloques(estados),
                "hoy": hoy_txt,
            }
        )

    base.update(
        turno={"id_turno": turno.id_turno},
        trabaja_hoy=trabaja_hoy,
        esperados=esperados,
        marcaron=marcaron,
        personas=personas,
    )
    return base


@router.get("/turnos/resumen")
def resumen(db: DbSession, regimen: Literal["7x7", "14x14"] = "7x7"):
    """Panel: bloques de trabajo de cada centro en las próximas dos semanas."""
    hoy_ = hoy()
    dias = ventana(hoy_)
    personas = _personas_por_turno(db)
    turnos = (
        db.query(Turno, Centro)
        .join(Centro, Turno.id_centro == Centro.id_centro)
        .filter(Turno.regimen == regimen)
        .order_by(Centro.tipo.desc(), Centro.nombre, Turno.grupo)
        .all()
    )
    centros: dict[int, dict] = {}
    for turno, centro in turnos:
        c = centros.setdefault(
            centro.id_centro,
            {"id_centro": centro.id_centro, "nombre": centro.nombre, "grupos": []},
        )
        estados = [
            "turno" if trabaja(turno.regimen, turno.fecha_ancla, d) else None for d in dias
        ]
        c["grupos"].append(
            {
                "grupo": turno.grupo,
                "personas": personas.get(turno.id_turno, 0),
                "bloques": bloques(estados),
            }
        )
    return {
        "regimen": regimen,
        "dias": [d.isoformat() for d in dias],
        "letras": [DIAS[d.weekday()] for d in dias],
        "hoy_idx": dias.index(hoy_),
        "centros": list(centros.values()),
    }


class AsignarTurno(BaseModel):
    id_empleado: int
    id_turno: int | None  # null = sacar del turno


@router.post("/turnos/asignar")
def asignar(datos: AsignarTurno, db: DbSession):
    empleado = db.get(Empleado, datos.id_empleado)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if datos.id_turno is not None and db.get(Turno, datos.id_turno) is None:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if empleado.estado == "inactivo":
        raise HTTPException(status_code=409, detail="No se puede asignar turno a una persona inactiva")
    empleado.id_turno = datos.id_turno
    db.commit()
    return {"id_empleado": empleado.id_empleado, "id_turno": empleado.id_turno}


@router.get("/turnos/asignables")
def asignables(db: DbSession, q: Annotated[str | None, Query(max_length=100)] = None):
    """Personas para el diálogo «Asignar turno», con su turno actual."""
    query = (
        db.query(Empleado, Cargo.nombre, Area.nombre)
        .join(Cargo, Empleado.id_cargo == Cargo.id_cargo)
        .join(Area, Cargo.id_area == Area.id_area)
        .filter(Empleado.estado != "inactivo")
    )
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            Empleado.nombres.ilike(term) | Empleado.apellidos.ilike(term) | Empleado.rut.ilike(term)
        )
    filas = query.order_by(Empleado.apellidos, Empleado.nombres).limit(20).all()
    return [
        {
            "id_empleado": e.id_empleado,
            "nombre": f"{e.nombres} {e.apellidos}",
            "cargo": cargo,
            "area": area,
            "id_turno": e.id_turno,
        }
        for e, cargo, area in filas
    ]
