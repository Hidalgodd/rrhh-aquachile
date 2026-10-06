import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_rrhh
from app.models.postulante import Postulante

router = APIRouter(prefix="/api/postulantes", tags=["Postulantes"])

# Carpeta donde se guardan los CV (backend/uploads/cvs)
CARPETA_CV = Path(__file__).resolve().parents[2] / "uploads" / "cvs"
CARPETA_CV.mkdir(parents=True, exist_ok=True)

EXTENSIONES_PERMITIDAS = {".pdf", ".doc", ".docx"}
TAMANO_MAXIMO = 5 * 1024 * 1024  # 5 MB


@router.post("", status_code=201)
async def crear_postulante(
    nombres: str = Form(...),
    apellidos: str = Form(...),
    correo: str = Form(...),
    cargo_postulado: str = Form(...),
    telefono: str | None = Form(None),
    cv: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1. Validar tipo de archivo
    extension = Path(cv.filename).suffix.lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(400, "El CV debe ser PDF, DOC o DOCX")

    # 2. Validar tamaño
    contenido = await cv.read()
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(400, "El CV no puede pesar más de 5 MB")

    # 3. Guardar con nombre único (evita que dos CV se llamen igual)
    nombre_guardado = f"{uuid.uuid4().hex}{extension}"
    (CARPETA_CV / nombre_guardado).write_bytes(contenido)

    # 4. Guardar los datos en la base de datos
    postulante = Postulante(
        nombres=nombres,
        apellidos=apellidos,
        correo=correo,
        telefono=telefono,
        cargo_postulado=cargo_postulado,
        cv_nombre_original=cv.filename,
        cv_archivo=nombre_guardado,
    )
    db.add(postulante)
    db.commit()
    db.refresh(postulante)
    return {"id_postulante": postulante.id_postulante, "mensaje": "Postulación recibida"}


@router.get("", dependencies=[Depends(require_rrhh)])
def listar_postulantes(db: Session = Depends(get_db)):
    postulantes = db.query(Postulante).order_by(Postulante.fecha_postulacion.desc()).all()
    return [
        {
            "id_postulante": p.id_postulante,
            "nombre": f"{p.nombres} {p.apellidos}",
            "correo": p.correo,
            "cargo_postulado": p.cargo_postulado,
            "estado": p.estado,
            "fecha_postulacion": p.fecha_postulacion,
        }
        for p in postulantes
    ]


@router.get("/{id_postulante}/cv", dependencies=[Depends(require_rrhh)])
def descargar_cv(id_postulante: int, db: Session = Depends(get_db)):
    p = db.get(Postulante, id_postulante)
    if not p:
        raise HTTPException(404, "Postulante no encontrado")
    ruta = CARPETA_CV / p.cv_archivo
    if not ruta.exists():
        raise HTTPException(404, "El archivo del CV no existe")
    return FileResponse(ruta, filename=p.cv_nombre_original)
