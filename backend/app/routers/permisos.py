from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies import (
    DbSession,
    empleado_actual,
    exigir_acceso_a,
    get_current_user,
    require_rrhh,
)
from app.models.empleado import Area, Cargo, Empleado
from app.models.rrhh import Centro, Permiso, Turno
from app.models.usuario import Usuario
from app.services.calendario import lunes_de
from app.services.vacaciones import TIPOS, saldo, validar_solicitud
from app.tiempo import ahora, hoy

router = APIRouter(prefix="/api/permisos", tags=["Permisos y vacaciones"])

TipoPermiso = Literal["vacaciones", "licencia medica", "administrativo"]
DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie"]


class SolicitudCreate(BaseModel):
    tipo: TipoPermiso
    fecha_inicio: date
    fecha_termino: date


class Resolucion(BaseModel):
    estado: Literal["aprobado", "rechazado"]
    comentario: str | None = Field(default=None, max_length=500)


def _fila(p: Permiso) -> dict:
    return {
        "id_permiso": p.id_permiso,
        "tipo": p.tipo,
        "tipo_label": TIPOS[p.tipo],
        "fecha_inicio": p.fecha_inicio,
        "fecha_termino": p.fecha_termino,
        "dias": p.dias,
        "estado": p.estado,
        "comentario_respuesta": p.comentario_respuesta,
        "fecha_solicitud": p.fecha_solicitud,
    }


# ---- Lo que hace cada persona con sus propias solicitudes ----------------------

@router.get("/calculo")
def calculo(
    tipo: TipoPermiso,
    desde: date,
    hasta: date,
    empleado: Annotated[Empleado, Depends(empleado_actual)],
    db: DbSession,
):
    """Vista previa del formulario: días hábiles, saldo resultante y cruce con el turno."""
    try:
        info = validar_solicitud(db, empleado, tipo, desde, hasta)
    except ValueError as exc:
        return {"valido": False, "mensaje": str(exc)}
    return {"valido": True, "mensaje": None, **info}


@router.post("", status_code=201)
def solicitar(
    datos: SolicitudCreate,
    empleado: Annotated[Empleado, Depends(empleado_actual)],
    db: DbSession,
):
    try:
        info = validar_solicitud(db, empleado, datos.tipo, datos.fecha_inicio, datos.fecha_termino)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    permiso = Permiso(
        id_empleado=empleado.id_empleado,
        tipo=datos.tipo,
        fecha_inicio=datos.fecha_inicio,
        fecha_termino=datos.fecha_termino,
        dias=info["dias"],
        estado="pendiente",
        fecha_solicitud=ahora(),
    )
    db.add(permiso)
    db.commit()
    db.refresh(permiso)
    return _fila(permiso)


@router.get("/mios")
def mis_solicitudes(
    empleado: Annotated[Empleado, Depends(empleado_actual)],
    db: DbSession,
):
    filas = (
        db.query(Permiso)
        .filter(Permiso.id_empleado == empleado.id_empleado)
        .order_by(Permiso.fecha_inicio.desc())
        .limit(50)
        .all()
    )
    return {"saldo": saldo(db, empleado.id_empleado), "solicitudes": [_fila(p) for p in filas]}


@router.delete("/{id_permiso}")
def cancelar(
    id_permiso: int,
    empleado: Annotated[Empleado, Depends(empleado_actual)],
    db: DbSession,
):
    p = db.get(Permiso, id_permiso)
    if p is None or p.id_empleado != empleado.id_empleado:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if p.estado != "pendiente":
        raise HTTPException(status_code=409, detail="Solo se pueden cancelar solicitudes pendientes")
    db.delete(p)
    db.commit()
    return {"ok": True}


# ---- Bandeja de aprobaciones (RR. HH. y administración) ------------------------

def _grupo_de(db: Session, e: Empleado) -> tuple[str, list[int]]:
    """Etiqueta y miembros del grupo con el que se compara la ausencia."""
    if e.id_turno:
        turno = db.get(Turno, e.id_turno)
        ids = [
            i
            for (i,) in db.query(Empleado.id_empleado).filter(
                Empleado.id_turno == e.id_turno, Empleado.estado != "inactivo"
            )
        ]
        return f"Grupo {turno.grupo}", ids
    cargo = db.get(Cargo, e.id_cargo)
    ids = [
        i
        for (i,) in db.query(Empleado.id_empleado)
        .join(Cargo, Empleado.id_cargo == Cargo.id_cargo)
        .filter(Cargo.id_area == cargo.id_area, Empleado.estado != "inactivo")
    ]
    return db.get(Area, cargo.id_area).nombre, ids


@router.get("", dependencies=[Depends(require_rrhh)])
def bandeja(
    db: DbSession,
    estado: Annotated[Literal["pendiente", "aprobado", "rechazado"], Query()] = "pendiente",
):
    filas = (
        db.query(Permiso, Empleado, Cargo.nombre, Area.nombre, Turno, Centro)
        .join(Empleado, Permiso.id_empleado == Empleado.id_empleado)
        .join(Cargo, Empleado.id_cargo == Cargo.id_cargo)
        .join(Area, Cargo.id_area == Area.id_area)
        .outerjoin(Turno, Empleado.id_turno == Turno.id_turno)
        .outerjoin(Centro, Turno.id_centro == Centro.id_centro)
        .filter(Permiso.estado == estado)
        .order_by(Permiso.fecha_inicio, Permiso.id_permiso)
        .all()
    )
    conteos = {
        e: db.query(Permiso).filter(Permiso.estado == e).count()
        for e in ("pendiente", "aprobado", "rechazado")
    }
    items = []
    for p, e, cargo, area, turno, centro in filas:
        s = saldo(db, e.id_empleado, p.fecha_inicio.year)
        items.append(
            {
                **_fila(p),
                "id_empleado": e.id_empleado,
                "nombre": f"{e.nombres.split()[0]} {e.apellidos.split()[0]}",
                "iniciales": (e.nombres[0] + e.apellidos[0]).upper(),
                "cargo": cargo,
                "area": area,
                "grupo": turno.grupo if turno else None,
                "centro": centro.nombre if centro else None,
                "saldo_quedaria": (
                    s["disponibles"] - (p.dias if p.estado == "pendiente" else 0)
                    if p.tipo == "vacaciones"
                    else None
                ),
            }
        )
    return {"conteos": conteos, "solicitudes": items}


@router.get("/{id_permiso}/impacto", dependencies=[Depends(require_rrhh)])
def impacto(id_permiso: int, db: DbSession):
    """Cuántas personas del grupo faltarían cada día de la semana de la solicitud."""
    p = db.get(Permiso, id_permiso)
    if p is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    e = db.get(Empleado, p.id_empleado)
    etiqueta, ids = _grupo_de(db, e)

    lunes = lunes_de(p.fecha_inicio)
    viernes = lunes + timedelta(days=4)
    otros = (
        db.query(Permiso)
        .filter(
            Permiso.id_empleado.in_(ids),
            Permiso.id_empleado != p.id_empleado,
            Permiso.estado == "aprobado",
            Permiso.fecha_inicio <= viernes,
            Permiso.fecha_termino >= lunes,
        )
        .all()
    )
    dias = []
    for i in range(5):
        d = lunes + timedelta(days=i)
        propio = p.estado != "rechazado" and p.fecha_inicio <= d <= p.fecha_termino
        ausentes = len({o.id_empleado for o in otros if o.fecha_inicio <= d <= o.fecha_termino})
        dias.append(
            {
                "fecha": d,
                "dia": DIAS_CORTOS[i],
                "ausentes": ausentes + (1 if propio else 0),
                "es_solicitud": propio,
            }
        )
    return {
        "grupo": etiqueta,
        "total": len(ids),
        "maximo": max(d["ausentes"] for d in dias),
        "dias": dias,
    }


@router.patch("/{id_permiso}/resolver")
def resolver(
    id_permiso: int,
    datos: Resolucion,
    usuario: Annotated[Usuario, Depends(require_rrhh)],
    db: DbSession,
):
    p = db.get(Permiso, id_permiso)
    if p is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    if p.estado != "pendiente":
        raise HTTPException(status_code=409, detail="Esta solicitud ya fue respondida")
    if datos.estado == "aprobado" and p.tipo == "vacaciones":
        s = saldo(db, p.id_empleado, p.fecha_inicio.year)
        if p.dias > s["disponibles"]:
            raise HTTPException(
                status_code=409,
                detail=f"No hay saldo suficiente: pide {p.dias} y tiene {s['disponibles']} disponibles",
            )
    p.estado = datos.estado
    p.comentario_respuesta = (datos.comentario or "").strip() or None
    p.id_resuelto_por = usuario.id_usuario
    p.fecha_respuesta = ahora()
    db.commit()
    return _fila(p)


# ---- Ficha de una persona (RR. HH. o la propia persona) -------------------------

@router.get("/de/{id_empleado}")
def de_empleado(
    id_empleado: int,
    usuario: Annotated[Usuario, Depends(get_current_user)],
    db: DbSession,
):
    exigir_acceso_a(usuario, id_empleado)
    filas = (
        db.query(Permiso)
        .filter(Permiso.id_empleado == id_empleado)
        .order_by(Permiso.fecha_inicio.desc())
        .limit(50)
        .all()
    )
    return {"saldo": saldo(db, id_empleado), "solicitudes": [_fila(p) for p in filas]}
