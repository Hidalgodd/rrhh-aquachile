from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.dependencies import DbSession, require_rrhh
from app.models.empleado import Empleado
from app.models.rrhh import Contrato
from app.tiempo import hoy

router = APIRouter(
    prefix="/api",
    tags=["Contratos"],
    dependencies=[Depends(require_rrhh)],
)

TipoContrato = Literal["indefinido", "plazo fijo", "por obra", "honorarios"]
ETIQUETA = {
    "indefinido": "Indefinido",
    "plazo fijo": "Plazo fijo",
    "por obra": "Por obra",
    "honorarios": "Honorarios",
}


class ContratoCreate(BaseModel):
    tipo: TipoContrato
    titulo: str | None = Field(default=None, max_length=100)
    fecha_inicio: date
    fecha_fin: date | None = None
    sueldo: Decimal = Field(ge=0, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def fechas(self):
        if self.tipo in {"plazo fijo", "por obra", "honorarios"} and self.fecha_fin is None:
            raise ValueError("Este tipo de contrato necesita fecha de término")
        if self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("La fecha de término no puede ser anterior al inicio")
        return self


class Renovacion(BaseModel):
    tipo: TipoContrato | None = None
    fecha_fin: date | None = None
    sueldo: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


def _estado(c: Contrato, hoy_: date) -> str:
    if c.fecha_inicio > hoy_:
        return "futuro"
    if c.fecha_fin is not None and c.fecha_fin < hoy_:
        return "terminado"
    return "vigente"


def _fila(c: Contrato, hoy_: date) -> dict:
    estado = _estado(c, hoy_)
    out = {
        "id_contrato": c.id_contrato,
        "tipo": c.tipo,
        "titulo": c.titulo or ETIQUETA[c.tipo],
        "fecha_inicio": c.fecha_inicio,
        "fecha_fin": c.fecha_fin,
        "sueldo": c.sueldo,
        "renovacion": c.renovacion,
        "estado": estado,
        "dias_restantes": None,
        "progreso": None,
    }
    if c.fecha_fin is not None:
        total = max((c.fecha_fin - c.fecha_inicio).days, 1)
        out["dias_restantes"] = max((c.fecha_fin - hoy_).days, 0)
        out["progreso"] = round(min(max((hoy_ - c.fecha_inicio).days / total, 0), 1), 4)
    return out


def _empleado_o_404(db, id_empleado: int) -> Empleado:
    e = db.get(Empleado, id_empleado)
    if e is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return e


@router.get("/empleados/{id_empleado}/contratos")
def contratos_de(id_empleado: int, db: DbSession):
    _empleado_o_404(db, id_empleado)
    hoy_ = hoy()
    filas = (
        db.query(Contrato)
        .filter(Contrato.id_empleado == id_empleado)
        .order_by(Contrato.fecha_inicio.desc())
        .all()
    )
    items = [_fila(c, hoy_) for c in filas]
    vigente = next((c for c in items if c["estado"] == "vigente"), None)
    return {"vigente": vigente, "historial": items}


@router.post("/empleados/{id_empleado}/contratos", status_code=201)
def crear_contrato(id_empleado: int, datos: ContratoCreate, db: DbSession):
    _empleado_o_404(db, id_empleado)
    hoy_ = hoy()
    existentes = db.query(Contrato).filter(Contrato.id_empleado == id_empleado).all()
    for c in existentes:
        fin = c.fecha_fin or date.max
        nuevo_fin = datos.fecha_fin or date.max
        if c.fecha_inicio <= nuevo_fin and datos.fecha_inicio <= fin:
            raise HTTPException(
                status_code=409,
                detail="Las fechas se cruzan con otro contrato; usa «Renovar contrato»",
            )
    c = Contrato(id_empleado=id_empleado, **datos.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _fila(c, hoy_)


@router.post("/contratos/{id_contrato}/renovar", status_code=201)
def renovar(id_contrato: int, datos: Renovacion, db: DbSession):
    anterior = db.get(Contrato, id_contrato)
    if anterior is None:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    if anterior.fecha_fin is None:
        raise HTTPException(status_code=409, detail="Un contrato indefinido no se renueva")
    if anterior.renovacion != "pendiente":
        raise HTTPException(status_code=409, detail="Este contrato ya tiene una decisión de renovación")

    tipo = datos.tipo or anterior.tipo
    inicio = anterior.fecha_fin + timedelta(days=1)
    if tipo != "indefinido" and (datos.fecha_fin is None or datos.fecha_fin < inicio):
        raise HTTPException(
            status_code=400,
            detail=f"Indica una fecha de término posterior al {inicio.strftime('%d-%m-%Y')}",
        )
    nuevo = Contrato(
        id_empleado=anterior.id_empleado,
        tipo=tipo,
        titulo=anterior.titulo if tipo == anterior.tipo else None,
        fecha_inicio=inicio,
        fecha_fin=None if tipo == "indefinido" else datos.fecha_fin,
        sueldo=datos.sueldo if datos.sueldo is not None else anterior.sueldo,
    )
    anterior.renovacion = "renovado"
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _fila(nuevo, hoy())


@router.post("/contratos/{id_contrato}/dejar-vencer")
def dejar_vencer(id_contrato: int, db: DbSession):
    c = db.get(Contrato, id_contrato)
    if c is None:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    if c.fecha_fin is None:
        raise HTTPException(status_code=409, detail="Un contrato indefinido no vence")
    if c.renovacion == "renovado":
        raise HTTPException(status_code=409, detail="Este contrato ya fue renovado")
    c.renovacion = "no_renovar"
    db.commit()
    return _fila(c, hoy())
