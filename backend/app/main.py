from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine
from app.models import empleado, postulante, rrhh, usuario  # noqa: F401
from app.routers import (
    asistencia,
    auth,
    contratos,
    dashboard,
    documentos,
    empleados,
    permisos,
    portal,
    postulantes,
    turnos,
)

app = FastAPI(title="RRHH AquaChile")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(postulantes.router)
app.include_router(auth.router)
app.include_router(empleados.router)
app.include_router(dashboard.router)
app.include_router(turnos.router)
app.include_router(permisos.router)
app.include_router(asistencia.router)
app.include_router(contratos.router)
app.include_router(documentos.router)
app.include_router(portal.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        return {"db": conn.execute(text("SELECT 1")).scalar()}