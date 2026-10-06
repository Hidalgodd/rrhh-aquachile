import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app import main


def test_health_returns_ok():
    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_postulante_reads_require_authentication():
    with TestClient(main.app) as client:
        list_response = client.get("/api/postulantes")
        cv_response = client.get("/api/postulantes/1/cv")
        employees_response = client.get("/api/empleados")

    assert list_response.status_code == 401
    assert cv_response.status_code == 401
    assert employees_response.status_code == 401


def test_db_check_executes_query(monkeypatch):
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(main, "engine", test_engine)

    with TestClient(main.app) as client:
        response = client.get("/db-check")

    test_engine.dispose()
    assert response.status_code == 200
    assert response.json() == {"db": 1}
