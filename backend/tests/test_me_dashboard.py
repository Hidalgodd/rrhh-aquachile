import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import empleado, postulante, usuario  # noqa: F401
from app.models.empleado import Area, Cargo, Empleado
from app.models.usuario import Usuario
from app.security import hash_password


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    with Session() as db:
        area = Area(nombre="Producción")
        db.add(area)
        db.flush()
        cargo = Cargo(nombre="Operario", id_area=area.id_area, sueldo_base=650000)
        db.add(cargo)
        db.flush()
        emp = Empleado(
            rut="11111111-1",
            nombres="Ana",
            apellidos="Pérez",
            correo="ana@example.com",
            id_cargo=cargo.id_cargo,
        )
        db.add(emp)
        db.flush()
        db.add(
            Usuario(
                id_empleado=emp.id_empleado,
                username="admin",
                password_hash=hash_password("clave-segura-123"),
                rol="admin",
            )
        )
        db.commit()

    def override_get_db():
        with Session() as db:
            yield db

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()
    engine.dispose()


def _token(client):
    r = client.post(
        "/api/auth/token", data={"username": "admin", "password": "clave-segura-123"}
    )
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_me_devuelve_nombre_y_rol(client):
    r = client.get("/api/auth/me", headers=_token(client))
    assert r.status_code == 200
    assert r.json()["nombre"] == "Ana Pérez"
    assert r.json()["rol"] == "admin"


def test_me_requiere_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_resumen_dashboard(client):
    r = client.get("/api/dashboard/resumen", headers=_token(client))
    assert r.status_code == 200
    body = r.json()
    assert body["activos"] == 1
    assert body["por_area"] == [{"area": "Producción", "total": 1}]


def test_resumen_requiere_login(client):
    assert client.get("/api/dashboard/resumen").status_code == 401
