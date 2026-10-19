import uuid
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.dependencies import (
    DbSession,
    empleado_actual,
    exigir_acceso_a,
    get_current_user,
    require_rrhh,
)
from app.models.empleado import Empleado
from app.models.rrhh import Documento
from app.models.usuario import Usuario
from app.tiempo import hoy

router = APIRouter(prefix="/api", tags=["Documentos"])

CARPETA = Path(__file__).resolve().parents[2] / "uploads" / "documentos"
CARPETA.mkdir(parents=True, exist_ok=True)
EXTENSIONES = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"}
TAMANO_MAXIMO = 10 * 1024 * 1024
TIPOS = {"contrato", "anexo", "liquidacion", "identidad", "otro"}


def _fila(d: Documento) -> dict:
    return {
        "id_documento": d.id_documento,
        "tipo": d.tipo,
        "titulo": d.titulo,
        "estado": d.estado,
        "fecha_emision": d.fecha_emision,
        "fecha_firma": d.fecha_firma,
        "tiene_archivo": bool(d.archivo),
    }


def _de(db, id_empleado: int) -> list[dict]:
    filas = (
        db.query(Documento)
        .filter(Documento.id_empleado == id_empleado)
        .order_by(Documento.fecha_emision.desc(), Documento.id_documento.desc())
        .all()
    )
    return [_fila(d) for d in filas]


@router.get("/documentos/mios")
def mis_documentos(empleado: Annotated[Empleado, Depends(empleado_actual)], db: DbSession):
    return _de(db, empleado.id_empleado)


@router.get("/empleados/{id_empleado}/documentos", dependencies=[Depends(require_rrhh)])
def documentos_de(id_empleado: int, db: DbSession):
    if db.get(Empleado, id_empleado) is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return _de(db, id_empleado)


@router.post(
    "/empleados/{id_empleado}/documentos",
    status_code=201,
    dependencies=[Depends(require_rrhh)],
)
async def subir_documento(
    id_empleado: int,
    db: DbSession,
    titulo: Annotated[str, Form(min_length=2, max_length=150)],
    tipo: Annotated[str, Form()] = "otro",
    enviar_a_firma: Annotated[bool, Form()] = False,
    archivo: UploadFile | None = File(None),
):
    if db.get(Empleado, id_empleado) is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if tipo not in TIPOS:
        raise HTTPException(status_code=400, detail="Tipo de documento no válido")

    guardado = original = None
    if archivo is not None and archivo.filename:
        ext = Path(archivo.filename).suffix.lower()
        if ext not in EXTENSIONES:
            raise HTTPException(status_code=400, detail="El archivo debe ser PDF, imagen, DOC o DOCX")
        contenido = await archivo.read()
        if len(contenido) > TAMANO_MAXIMO:
            raise HTTPException(status_code=400, detail="El archivo no puede pesar más de 10 MB")
        guardado = f"{uuid.uuid4().hex}{ext}"
        (CARPETA / guardado).write_bytes(contenido)
        original = archivo.filename
    elif not enviar_a_firma:
        raise HTTPException(status_code=400, detail="Adjunta un archivo")

    d = Documento(
        id_empleado=id_empleado,
        tipo=tipo,
        titulo=titulo.strip(),
        estado="pendiente_firma" if enviar_a_firma else "al_dia",
        fecha_emision=hoy(),
        archivo=guardado,
        archivo_original=original,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return _fila(d)


@router.post("/documentos/{id_documento}/firmar")
def firmar(
    id_documento: int,
    empleado: Annotated[Empleado, Depends(empleado_actual)],
    db: DbSession,
):
    d = db.get(Documento, id_documento)
    if d is None or d.id_empleado != empleado.id_empleado:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if d.estado != "pendiente_firma":
        raise HTTPException(status_code=409, detail="Este documento no está esperando tu firma")
    d.estado = "firmado"
    d.fecha_firma = hoy()
    db.commit()
    return _fila(d)


@router.get("/documentos/{id_documento}/archivo")
def descargar(
    id_documento: int,
    usuario: Annotated[Usuario, Depends(get_current_user)],
    db: DbSession,
):
    d = db.get(Documento, id_documento)
    if d is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    exigir_acceso_a(usuario, d.id_empleado)
    if not d.archivo or not (CARPETA / d.archivo).exists():
        raise HTTPException(status_code=404, detail="Este documento aún no tiene archivo")
    return FileResponse(CARPETA / d.archivo, filename=d.archivo_original or d.archivo)
