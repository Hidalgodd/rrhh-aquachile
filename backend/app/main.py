from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine
from app.models import empleado, postulante, usuario  # noqa: F401
from app.routers import auth, empleados, postulantes

app = FastAPI(title="RRHH AquaChile")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(postulantes.router)
app.include_router(auth.router)
app.include_router(empleados.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        return {"db": conn.execute(text("SELECT 1")).scalar()}