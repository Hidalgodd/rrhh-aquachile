from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.dependencies import (
    DbSession,
    empleado_actual,
    exigir_acceso_a,
    get_current_user,
)
from app.models.empleado import Area, Cargo, Empleado
from app.models.rrhh import Centro, Contrato, Turno
from app.models.usuario import Usuario
from app.services import certificado
from app.services.vacaciones import saldo
from app.tiempo import hoy

router = APIRouter(prefix="/api", tags=["Portal del colaborador"])


def _contexto(db: Session, e: Empleado) -> dict:
    cargo = db.get(Cargo, e.id_cargo)
    area = db.get(Area, cargo.id_area)
    turno = db.get(Turno, e.id_turno) if e.id_turno else None
    centro = db.get(Centro, turno.id_centro) if turno else None
    return {
        "id_empleado": e.id_empleado,
        "nombre": f"{e.nombres} {e.apellidos}",
        "primer_nombre": e.nombres.split()[0],
        "cargo": cargo.nombre,
        "area": area.nombre,
        "centro": centro.nombre if centro else None,
        "grupo": turno.grupo if turno else None,
        "regimen": turno.regimen if turno else None,
    }


@router.get("/me/resumen")
def resumen(empleado: Annotated[Empleado, Depends(empleado_actual)], db: DbSession):
    return {**_contexto(db, empleado), "saldo": saldo(db, empleado.id_empleado)}


def _certificado(db: Session, e: Empleado) -> Response:
    ctx = _contexto(db, e)
    contrato = (
        db.query(Contrato)
        .filter(Contrato.id_empleado == e.id_empleado, Contrato.fecha_inicio <= hoy())
        .order_by(Contrato.fecha_inicio.desc())
        .first()
    )
    pdf = certificado.generar(
        nombre=ctx["nombre"],
        rut=e.rut,
        cargo=ctx["cargo"],
        area=ctx["area"],
        ingreso=e.fecha_ingreso,
        tipo_contrato=contrato.tipo if contrato else None,
        hoy=hoy(),
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="certificado-antiguedad.pdf"'},
    )


@router.get("/me/certificado-antiguedad")
def mi_certificado(empleado: Annotated[Empleado, Depends(empleado_actual)], db: DbSession):
    return _certificado(db, empleado)


@router.get("/empleados/{id_empleado}/certificado-antiguedad")
def certificado_de(
    id_empleado: int,
    usuario: Annotated[Usuario, Depends(get_current_user)],
    db: DbSession,
):
    exigir_acceso_a(usuario, id_empleado)
    e = db.get(Empleado, id_empleado)
    if e is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return _certificado(db, e)
