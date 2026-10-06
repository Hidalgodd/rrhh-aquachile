import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.dependencies import require_rrhh
from app.models import empleado, postulante, usuario  # noqa: F401


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        with test_session() as db:
            yield db

    main.app.dependency_overrides[get_db] = override_get_db
    main.app.dependency_overrides[require_rrhh] = lambda: None
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_creates_and_filters_employee(client):
    area_response = client.post(
        "/api/areas",
        json={"nombre": "Producción", "descripcion": "Operaciones"},
    )
    assert area_response.status_code == 201

    cargo_response = client.post(
        "/api/cargos",
        json={
            "nombre": "Operario de planta",
            "id_area": area_response.json()["id_area"],
            "sueldo_base": "650000.00",
        },
    )
    assert cargo_response.status_code == 201
    assert cargo_response.json()["area_nombre"] == "Producción"

    employee_response = client.post(
        "/api/empleados",
        json={
            "rut": "11.111.111-1",
            "nombres": "Ana",
            "apellidos": "Pérez",
            "correo": " ANA.PEREZ@example.com ",
            "id_cargo": cargo_response.json()["id_cargo"],
        },
    )
    assert employee_response.status_code == 201
    assert employee_response.json()["rut"] == "11111111-1"
    assert employee_response.json()["correo"] == "ana.perez@example.com"

    list_response = client.get("/api/empleados", params={"q": "ANA", "estado": "activo"})
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["cargo"] == "Operario de planta"


def test_rejects_invalid_rut_and_duplicate_area(client):
    area_payload = {"nombre": "Finanzas", "descripcion": None}
    assert client.post("/api/areas", json=area_payload).status_code == 201
    duplicate_response = client.post("/api/areas", json=area_payload)
    assert duplicate_response.status_code == 409

    invalid_employee = client.post(
        "/api/empleados",
        json={
            "rut": "11.111.111-2",
            "nombres": "Luis",
            "apellidos": "Soto",
            "correo": "luis@example.com",
            "id_cargo": 1,
        },
    )
    assert invalid_employee.status_code == 422


def test_employee_update_requires_non_null_fields(client):
    area_id = client.post("/api/areas", json={"nombre": "Operaciones"}).json()["id_area"]
    cargo_id = client.post(
        "/api/cargos",
        json={"nombre": "Técnico", "id_area": area_id, "sueldo_base": "500000"},
    ).json()["id_cargo"]
    employee_id = client.post(
        "/api/empleados",
        json={
            "rut": "12.345.678-5",
            "nombres": "María",
            "apellidos": "Rojas",
            "correo": "maria@example.com",
            "id_cargo": cargo_id,
        },
    ).json()["id_empleado"]

    null_name_response = client.patch(
        f"/api/empleados/{employee_id}",
        json={"nombres": None},
    )
    inactive_response = client.patch(
        f"/api/empleados/{employee_id}",
        json={"estado": "inactivo"},
    )

    assert null_name_response.status_code == 422
    assert inactive_response.status_code == 200
    assert inactive_response.json()["estado"] == "inactivo"
