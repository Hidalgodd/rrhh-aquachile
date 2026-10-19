from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_rrhh
from app.models.empleado import Area, Cargo, Empleado
from app.models.rrhh import Centro, Turno
from app.models.usuario import Usuario
from app.tiempo import hoy
from app.schemas.empleado import (
    AreaCreate,
    AreaRead,
    CargoCreate,
    CargoRead,
    EmpleadoCreate,
    EmpleadoRead,
    EmpleadoUpdate,
)

router = APIRouter(
    prefix="/api",
    tags=["Estructura organizacional y empleados"],
    dependencies=[Depends(require_rrhh)],
)
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/areas", response_model=list[AreaRead])
def listar_areas(db: DbSession):
    return db.query(Area).order_by(Area.nombre).all()


@router.post("/areas", response_model=AreaRead, status_code=status.HTTP_201_CREATED)
def crear_area(datos: AreaCreate, db: DbSession):
    area = Area(nombre=datos.nombre, descripcion=datos.descripcion)
    db.add(area)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un área con ese nombre",
        ) from exc
    db.refresh(area)
    return area


@router.get("/cargos", response_model=list[CargoRead])
def listar_cargos(
    db: DbSession,
    id_area: Annotated[int | None, Query(gt=0)] = None,
):
    query = db.query(Cargo, Area.nombre).join(Area, Cargo.id_area == Area.id_area)
    if id_area is not None:
        query = query.filter(Cargo.id_area == id_area)
    return [
        {
            "id_cargo": cargo.id_cargo,
            "nombre": cargo.nombre,
            "id_area": cargo.id_area,
            "sueldo_base": cargo.sueldo_base,
            "area_nombre": area_nombre,
        }
        for cargo, area_nombre in query.order_by(Area.nombre, Cargo.nombre).all()
    ]


@router.post("/cargos", response_model=CargoRead, status_code=status.HTTP_201_CREATED)
def crear_cargo(datos: CargoCreate, db: DbSession):
    area = db.get(Area, datos.id_area)
    if area is None:
        raise HTTPException(status_code=404, detail="Área no encontrada")

    cargo = Cargo(
        nombre=datos.nombre,
        id_area=datos.id_area,
        sueldo_base=datos.sueldo_base,
    )
    db.add(cargo)
    db.commit()
    db.refresh(cargo)
    return {
        "id_cargo": cargo.id_cargo,
        "nombre": cargo.nombre,
        "id_area": cargo.id_area,
        "sueldo_base": cargo.sueldo_base,
        "area_nombre": area.nombre,
    }


def _consulta(db: Session):
    return (
        db.query(Empleado, Cargo, Area, Turno, Centro)
        .join(Cargo, Empleado.id_cargo == Cargo.id_cargo)
        .join(Area, Cargo.id_area == Area.id_area)
        .outerjoin(Turno, Empleado.id_turno == Turno.id_turno)
        .outerjoin(Centro, Turno.id_centro == Centro.id_centro)
    )


def _respuesta(fila) -> EmpleadoRead:
    empleado, cargo, area, turno, centro = fila
    return EmpleadoRead(
        id_empleado=empleado.id_empleado,
        rut=empleado.rut,
        nombres=empleado.nombres,
        apellidos=empleado.apellidos,
        fecha_nacimiento=empleado.fecha_nacimiento,
        correo=empleado.correo,
        telefono=empleado.telefono,
        direccion=empleado.direccion,
        fecha_ingreso=empleado.fecha_ingreso,
        estado=empleado.estado,
        id_cargo=empleado.id_cargo,
        cargo=cargo.nombre,
        id_area=area.id_area,
        area=area.nombre,
        id_turno=empleado.id_turno,
        centro=centro.nombre if centro else None,
        grupo=turno.grupo if turno else None,
        regimen=turno.regimen if turno else None,
        fecha_salida=empleado.fecha_salida,
    )


def _obtener_empleado_con_detalle(db: Session, empleado: Empleado) -> EmpleadoRead:
    fila = _consulta(db).filter(Empleado.id_empleado == empleado.id_empleado).first()
    if fila is None:
        raise HTTPException(status_code=409, detail="El cargo o área asociado ya no existe")
    return _respuesta(fila)


@router.get("/empleados", response_model=list[EmpleadoRead])
def listar_empleados(
    db: DbSession,
    q: Annotated[str | None, Query(max_length=100)] = None,
    estado: Annotated[str | None, Query(pattern="^(activo|inactivo|licencia)$")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
):
    query = _consulta(db)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            (Empleado.nombres.ilike(term))
            | (Empleado.apellidos.ilike(term))
            | (Empleado.rut.ilike(term))
            | (Empleado.correo.ilike(term))
        )
    if estado:
        query = query.filter(Empleado.estado == estado)
    filas = (
        query.order_by(Empleado.apellidos, Empleado.nombres)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_respuesta(f) for f in filas]


@router.post(
    "/empleados",
    response_model=EmpleadoRead,
    status_code=status.HTTP_201_CREATED,
)
def crear_empleado(datos: EmpleadoCreate, db: DbSession):
    if db.get(Cargo, datos.id_cargo) is None:
        raise HTTPException(status_code=404, detail="Cargo no encontrado")

    empleado = Empleado(**datos.model_dump())
    if empleado.estado == "inactivo":
        empleado.fecha_salida = hoy()
    db.add(empleado)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El RUT o correo ya está registrado",
        ) from exc
    db.refresh(empleado)
    return _obtener_empleado_con_detalle(db, empleado)


@router.get("/empleados/{id_empleado}", response_model=EmpleadoRead)
def obtener_empleado(id_empleado: int, db: DbSession):
    empleado = db.get(Empleado, id_empleado)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return _obtener_empleado_con_detalle(db, empleado)


@router.patch("/empleados/{id_empleado}", response_model=EmpleadoRead)
def actualizar_empleado(
    id_empleado: int,
    datos: EmpleadoUpdate,
    db: DbSession,
):
    empleado = db.get(Empleado, id_empleado)
    if empleado is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")
    if "id_cargo" in cambios and db.get(Cargo, cambios["id_cargo"]) is None:
        raise HTTPException(status_code=404, detail="Cargo no encontrado")

    for campo, valor in cambios.items():
        setattr(empleado, campo, valor)
    if cambios.get("estado") == "inactivo":
        empleado.fecha_salida = empleado.fecha_salida or hoy()
        usuario = db.query(Usuario).filter(Usuario.id_empleado == id_empleado).first()
        if usuario is not None:
            usuario.activo = False
    elif cambios.get("estado") in {"activo", "licencia"}:
        empleado.fecha_salida = None
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado",
        ) from exc
    db.refresh(empleado)
    return _obtener_empleado_con_detalle(db, empleado)
