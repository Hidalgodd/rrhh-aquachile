"""Turnos, permisos/vacaciones, contratos, documentos, asistencia, panel y certificado."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import empleado, postulante, rrhh, usuario  # noqa: F401
from app.models.empleado import Area, Cargo, Empleado
from app.models.rrhh import Centro, Permiso, Turno
from app.models.usuario import Usuario
from app.security import hash_password
from app.services.calendario import dias_habiles, es_habil, lunes_de
from app.services.turnos import bloques, trabaja
from app.tiempo import hoy

CLAVE = "clave-segura-123"
LUNES_PROXIMO = lunes_de(hoy()) + timedelta(days=7)


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    with Session() as db:
        area = Area(nombre="Procesamiento")
        db.add(area)
        db.flush()
        cargo = Cargo(nombre="Operaria de planta", id_area=area.id_area, sueldo_base=650000)
        db.add(cargo)
        centro = Centro(nombre="Planta Puerto Montt", tipo="planta")
        db.add(centro)
        db.flush()
        turno = Turno(id_centro=centro.id_centro, grupo="A", regimen="7x7", fecha_ancla=lunes_de(hoy()))
        db.add(turno)
        db.flush()
        id_turno = turno.id_turno

        def persona(nombres, apellidos, rut, correo, usuario_, rol, con_turno=True):
            e = Empleado(
                rut=rut, nombres=nombres, apellidos=apellidos, correo=correo, id_cargo=cargo.id_cargo,
                fecha_ingreso=date(2021, 3, 3), id_turno=turno.id_turno if con_turno else None,
            )
            db.add(e)
            db.flush()
            db.add(Usuario(id_empleado=e.id_empleado, username=usuario_,
                           password_hash=hash_password(CLAVE), rol=rol))
            return e.id_empleado

        ids = {
            "camila": persona("Camila", "Rojas", "15876321-8", "camila@x.cl", "admin", "admin", False),
            "paula": persona("Paula", "Aguilar", "12345678-5", "paula@x.cl", "paula", "empleado"),
            "luis": persona("Luis", "Díaz", "16789012-3", "luis@x.cl", "luis", "empleado"),
        }
        db.commit()

    def override_get_db():
        with Session() as db:
            yield db

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as c:

        def auth(usuario_):
            r = c.post("/api/auth/token", data={"username": usuario_, "password": CLAVE})
            assert r.status_code == 200
            return {"Authorization": f"Bearer {r.json()['access_token']}"}

        yield {"c": c, "ids": ids, "admin": auth("admin"), "paula": auth("paula"),
               "luis": auth("luis"), "Session": Session, "turno": id_turno}
    main.app.dependency_overrides.clear()
    engine.dispose()


def semana(lunes=LUNES_PROXIMO):
    return lunes, lunes + timedelta(days=4)


# ---- reglas puras --------------------------------------------------------------

def test_turno_7x7_alterna_semanas():
    ancla = date(2026, 10, 12)
    assert all(trabaja("7x7", ancla, ancla + timedelta(i)) for i in range(7))
    assert not any(trabaja("7x7", ancla, ancla + timedelta(i)) for i in range(7, 14))
    assert trabaja("7x7", ancla, ancla + timedelta(14))
    assert trabaja("7x7", ancla, ancla - timedelta(1)) is False  # el bloque anterior fue del otro grupo


def test_turno_14x14():
    ancla = date(2026, 10, 12)
    assert trabaja("14x14", ancla, ancla + timedelta(13))
    assert not trabaja("14x14", ancla, ancla + timedelta(14))
    assert trabaja("14x14", ancla, ancla + timedelta(28))


def test_bloques_unen_dias_contiguos():
    assert bloques(["turno", "turno", None, "vacaciones", "vacaciones"]) == [
        {"tipo": "turno", "inicio": 0, "fin": 1},
        {"tipo": "vacaciones", "inicio": 3, "fin": 4},
    ]


def test_dias_habiles_excluye_fin_de_semana_y_feriados():
    assert dias_habiles(date(2026, 10, 19), date(2026, 10, 23)) == 5
    assert dias_habiles(date(2026, 10, 19), date(2026, 10, 25)) == 5
    assert dias_habiles(date(2026, 12, 7), date(2026, 12, 11)) == 4  # 8 de diciembre
    assert not es_habil(date(2026, 9, 18))


# ---- vacaciones y permisos --------------------------------------------------------

def test_solicitud_calcula_dias_y_saldo(ctx):
    c, (ini, fin) = ctx["c"], semana()
    r = c.get("/api/permisos/calculo", headers=ctx["paula"],
              params={"tipo": "vacaciones", "desde": ini.isoformat(), "hasta": fin.isoformat()})
    esperado = dias_habiles(ini, fin)
    assert r.json()["valido"] is True
    assert r.json()["dias"] == esperado
    assert r.json()["saldo_quedaria"] == 15 - esperado
    assert r.json()["regimen"] == "7x7"


def test_flujo_completo_pedir_y_aprobar(ctx):
    c, (ini, fin) = ctx["c"], semana()
    creada = c.post("/api/permisos", headers=ctx["paula"],
                    json={"tipo": "vacaciones", "fecha_inicio": ini.isoformat(), "fecha_termino": fin.isoformat()})
    assert creada.status_code == 201
    assert creada.json()["estado"] == "pendiente"
    pid, dias = creada.json()["id_permiso"], creada.json()["dias"]

    mios = c.get("/api/permisos/mios", headers=ctx["paula"]).json()
    assert mios["saldo"]["en_tramite"] == dias and mios["saldo"]["usados"] == 0

    # la persona no puede ver ni resolver la bandeja
    assert c.get("/api/permisos", headers=ctx["paula"]).status_code == 403
    assert c.patch(f"/api/permisos/{pid}/resolver", headers=ctx["paula"], json={"estado": "aprobado"}).status_code == 403

    bandeja = c.get("/api/permisos", headers=ctx["admin"]).json()
    assert bandeja["conteos"]["pendiente"] == 1
    item = bandeja["solicitudes"][0]
    assert item["nombre"] == "Paula Aguilar" and item["grupo"] == "A" and item["saldo_quedaria"] == 15 - dias

    ok = c.patch(f"/api/permisos/{pid}/resolver", headers=ctx["admin"],
                 json={"estado": "aprobado", "comentario": "Que descanses"})
    assert ok.status_code == 200 and ok.json()["estado"] == "aprobado"
    assert c.patch(f"/api/permisos/{pid}/resolver", headers=ctx["admin"], json={"estado": "rechazado"}).status_code == 409

    mios = c.get("/api/permisos/mios", headers=ctx["paula"]).json()
    assert mios["saldo"]["usados"] == dias and mios["saldo"]["disponibles"] == 15 - dias
    assert mios["solicitudes"][0]["comentario_respuesta"] == "Que descanses"


def test_rechazos_de_solicitud(ctx):
    c, (ini, fin) = ctx["c"], semana()
    body = {"tipo": "vacaciones", "fecha_inicio": ini.isoformat(), "fecha_termino": fin.isoformat()}
    assert c.post("/api/permisos", headers=ctx["paula"], json=body).status_code == 201
    # se cruza con la anterior
    assert c.post("/api/permisos", headers=ctx["paula"], json=body).status_code == 400
    # término antes del inicio
    malo = {**body, "fecha_inicio": fin.isoformat(), "fecha_termino": ini.isoformat()}
    assert c.post("/api/permisos", headers=ctx["paula"], json=malo).status_code == 400
    # fechas pasadas (salvo licencia médica)
    pasado = {"tipo": "vacaciones", "fecha_inicio": "2020-01-06", "fecha_termino": "2020-01-10"}
    assert c.post("/api/permisos", headers=ctx["paula"], json=pasado).status_code == 400
    # un sábado y domingo no tienen días hábiles
    finde = LUNES_PROXIMO + timedelta(days=21 + 5)
    r = c.post("/api/permisos", headers=ctx["paula"],
               json={"tipo": "vacaciones", "fecha_inicio": finde.isoformat(),
                     "fecha_termino": (finde + timedelta(1)).isoformat()})
    assert r.status_code == 400 and "hábiles" in r.json()["detail"]


def test_no_se_pueden_pedir_mas_dias_que_el_saldo(ctx):
    c = ctx["c"]
    ini = LUNES_PROXIMO + timedelta(days=28)
    fin = ini
    while dias_habiles(ini, fin) < 16:
        fin += timedelta(days=1)
    r = c.post("/api/permisos", headers=ctx["paula"],
               json={"tipo": "vacaciones", "fecha_inicio": ini.isoformat(), "fecha_termino": fin.isoformat()})
    assert r.status_code == 400 and "No te alcanzan" in r.json()["detail"]
    # el permiso administrativo no descuenta vacaciones
    r = c.post("/api/permisos", headers=ctx["paula"],
               json={"tipo": "administrativo", "fecha_inicio": ini.isoformat(), "fecha_termino": ini.isoformat()})
    assert r.status_code == 201


def test_cancelar_solo_pendientes_y_propias(ctx):
    c, (ini, fin) = ctx["c"], semana()
    pid = c.post("/api/permisos", headers=ctx["paula"],
                 json={"tipo": "vacaciones", "fecha_inicio": ini.isoformat(),
                       "fecha_termino": fin.isoformat()}).json()["id_permiso"]
    assert c.delete(f"/api/permisos/{pid}", headers=ctx["luis"]).status_code == 404
    assert c.delete(f"/api/permisos/{pid}", headers=ctx["paula"]).status_code == 200
    assert c.get("/api/permisos/mios", headers=ctx["paula"]).json()["solicitudes"] == []


def test_impacto_cuenta_ausentes_del_grupo_por_dia(ctx):
    c, (ini, fin) = ctx["c"], semana()
    # Luis ya tiene aprobado el martes y miércoles
    with ctx["Session"]() as db:
        db.add(Permiso(id_empleado=ctx["ids"]["luis"], tipo="vacaciones",
                       fecha_inicio=ini + timedelta(1), fecha_termino=ini + timedelta(2),
                       dias=2, estado="aprobado"))
        db.commit()
    pid = c.post("/api/permisos", headers=ctx["paula"],
                 json={"tipo": "vacaciones", "fecha_inicio": ini.isoformat(),
                       "fecha_termino": fin.isoformat()}).json()["id_permiso"]
    r = c.get(f"/api/permisos/{pid}/impacto", headers=ctx["admin"]).json()
    assert r["grupo"] == "Grupo A" and r["total"] == 2
    assert [d["ausentes"] for d in r["dias"]] == [1, 2, 2, 1, 1]
    assert r["maximo"] == 2


def test_vista_de_ficha_ajena_prohibida(ctx):
    c, ids = ctx["c"], ctx["ids"]
    assert c.get(f"/api/permisos/de/{ids['luis']}", headers=ctx["paula"]).status_code == 403
    assert c.get(f"/api/permisos/de/{ids['paula']}", headers=ctx["paula"]).status_code == 200
    assert c.get(f"/api/permisos/de/{ids['luis']}", headers=ctx["admin"]).status_code == 200


# ---- turnos -----------------------------------------------------------------------

def test_grilla_muestra_turno_y_ausencias(ctx):
    c = ctx["c"]
    lunes = lunes_de(hoy())
    with ctx["Session"]() as db:
        db.add(Permiso(id_empleado=ctx["ids"]["luis"], tipo="vacaciones", fecha_inicio=lunes + timedelta(3),
                       fecha_termino=lunes + timedelta(6), dias=2, estado="aprobado"))
        db.commit()
    g = c.get("/api/turnos/grilla", headers=ctx["admin"], params={"grupo": "A", "regimen": "7x7"}).json()
    assert g["centro"]["nombre"] == "Planta Puerto Montt"
    assert len(g["dias"]) == 14 and g["letras"][0] == "L"
    por_nombre = {p["nombre"]: p for p in g["personas"]}
    assert por_nombre["Paula Aguilar"]["bloques"] == [{"tipo": "turno", "inicio": 0, "fin": 6}]
    assert por_nombre["Luis Díaz"]["bloques"] == [
        {"tipo": "turno", "inicio": 0, "fin": 2}, {"tipo": "vacaciones", "inicio": 3, "fin": 6}]
    assert g["trabaja_hoy"] is True
    # el grupo B no existe en este escenario: respuesta vacía, no error
    vacio = c.get("/api/turnos/grilla", headers=ctx["admin"], params={"grupo": "B"}).json()
    assert vacio["personas"] == [] and vacio["turno"] is None


def test_asistencia_marca_entrada_y_salida_y_aparece_en_la_grilla(ctx):
    c = ctx["c"]
    r1 = c.post("/api/asistencia/marcar", headers=ctx["paula"])
    assert r1.status_code == 200 and r1.json()["entrada"] and r1.json()["salida"] is None
    r2 = c.post("/api/asistencia/marcar", headers=ctx["paula"])
    assert r2.status_code == 200 and r2.json()["salida"]
    assert c.post("/api/asistencia/marcar", headers=ctx["paula"]).status_code == 409

    g = c.get("/api/turnos/grilla", headers=ctx["admin"], params={"grupo": "A"}).json()
    assert g["esperados"] == 2 and g["marcaron"] == 1
    assert {p["nombre"]: p["hoy"] for p in g["personas"]}["Luis Díaz"] == "Sin marcar"
    mia = c.get("/api/asistencia/mia", headers=ctx["paula"]).json()
    assert len(mia["registros"]) == 1


def test_asignar_turno_y_resumen_del_panel(ctx):
    c = ctx["c"]
    r = c.post("/api/turnos/asignar", headers=ctx["admin"],
               json={"id_empleado": ctx["ids"]["camila"], "id_turno": ctx["turno"]})
    assert r.status_code == 200
    resumen = c.get("/api/turnos/resumen", headers=ctx["admin"]).json()
    grupo = resumen["centros"][0]["grupos"][0]
    assert grupo["personas"] == 3 and grupo["bloques"][0]["inicio"] == 0
    assert c.post("/api/turnos/asignar", headers=ctx["paula"],
                  json={"id_empleado": 1, "id_turno": None}).status_code == 403


# ---- contratos, documentos, certificado ---------------------------------------------

def test_contrato_vigente_renovar_y_dejar_vencer(ctx):
    c, e = ctx["c"], ctx["ids"]["paula"]
    fin = hoy() + timedelta(days=30)
    nuevo = c.post(f"/api/empleados/{e}/contratos", headers=ctx["admin"],
                   json={"tipo": "plazo fijo", "fecha_inicio": (hoy() - timedelta(days=180)).isoformat(),
                         "fecha_fin": fin.isoformat(), "sueldo": "650000"})
    assert nuevo.status_code == 201
    # plazo fijo exige fecha de término
    assert c.post(f"/api/empleados/{e}/contratos", headers=ctx["admin"],
                  json={"tipo": "plazo fijo", "fecha_inicio": "2030-01-01", "sueldo": "1"}).status_code == 422
    # no se puede crear otro que se cruce
    assert c.post(f"/api/empleados/{e}/contratos", headers=ctx["admin"],
                  json={"tipo": "indefinido", "fecha_inicio": hoy().isoformat(), "sueldo": "1"}).status_code == 409

    datos = c.get(f"/api/empleados/{e}/contratos", headers=ctx["admin"]).json()
    v = datos["vigente"]
    assert v["dias_restantes"] == 30 and 0 < v["progreso"] < 1

    renovado = c.post(f"/api/contratos/{v['id_contrato']}/renovar", headers=ctx["admin"],
                      json={"fecha_fin": (fin + timedelta(days=180)).isoformat()})
    assert renovado.status_code == 201
    assert renovado.json()["fecha_inicio"] == (fin + timedelta(days=1)).isoformat()
    assert renovado.json()["estado"] == "futuro"
    # ya hay decisión: ni renovar ni dejar vencer de nuevo
    assert c.post(f"/api/contratos/{v['id_contrato']}/renovar", headers=ctx["admin"], json={}).status_code == 409
    assert c.post(f"/api/contratos/{v['id_contrato']}/dejar-vencer", headers=ctx["admin"]).status_code == 409
    assert len(c.get(f"/api/empleados/{e}/contratos", headers=ctx["admin"]).json()["historial"]) == 2
    # la persona no puede ver contratos por la API de RR. HH.
    assert c.get(f"/api/empleados/{e}/contratos", headers=ctx["paula"]).status_code == 403


def test_dejar_vencer(ctx):
    c, e = ctx["c"], ctx["ids"]["paula"]
    cid = c.post(f"/api/empleados/{e}/contratos", headers=ctx["admin"],
                 json={"tipo": "plazo fijo", "fecha_inicio": (hoy() - timedelta(days=10)).isoformat(),
                       "fecha_fin": (hoy() + timedelta(days=20)).isoformat(), "sueldo": "1"}).json()["id_contrato"]
    r = c.post(f"/api/contratos/{cid}/dejar-vencer", headers=ctx["admin"])
    assert r.status_code == 200 and r.json()["renovacion"] == "no_renovar"
    assert c.post(f"/api/contratos/{cid}/renovar", headers=ctx["admin"],
                  json={"fecha_fin": "2030-01-01"}).status_code == 409


def test_documentos_subir_firmar_y_descargar(ctx):
    c, e = ctx["c"], ctx["ids"]["paula"]
    sin_archivo = c.post(f"/api/empleados/{e}/documentos", headers=ctx["admin"],
                         data={"titulo": "Anexo de turno 7x7", "tipo": "anexo", "enviar_a_firma": "true"})
    assert sin_archivo.status_code == 201 and sin_archivo.json()["estado"] == "pendiente_firma"
    did = sin_archivo.json()["id_documento"]

    subido = c.post(f"/api/empleados/{e}/documentos", headers=ctx["admin"],
                    data={"titulo": "Cédula de identidad", "tipo": "identidad"},
                    files={"archivo": ("cedula.pdf", b"%PDF-1.4 prueba", "application/pdf")})
    assert subido.status_code == 201 and subido.json()["estado"] == "al_dia" and subido.json()["tiene_archivo"]
    assert c.post(f"/api/empleados/{e}/documentos", headers=ctx["admin"],
                  data={"titulo": "Virus", "tipo": "otro"},
                  files={"archivo": ("a.exe", b"MZ", "application/octet-stream")}).status_code == 400

    assert len(c.get("/api/documentos/mios", headers=ctx["paula"]).json()) == 2
    assert c.post(f"/api/documentos/{did}/firmar", headers=ctx["luis"]).status_code == 404
    firmado = c.post(f"/api/documentos/{did}/firmar", headers=ctx["paula"])
    assert firmado.json()["estado"] == "firmado" and firmado.json()["fecha_firma"] == hoy().isoformat()
    assert c.post(f"/api/documentos/{did}/firmar", headers=ctx["paula"]).status_code == 409

    archivo = subido.json()["id_documento"]
    assert c.get(f"/api/documentos/{archivo}/archivo", headers=ctx["paula"]).content.startswith(b"%PDF")
    assert c.get(f"/api/documentos/{archivo}/archivo", headers=ctx["luis"]).status_code == 403


def test_certificado_de_antiguedad_es_un_pdf(ctx):
    c = ctx["c"]
    r = c.get("/api/me/certificado-antiguedad", headers=ctx["paula"])
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert "attachment" in r.headers["content-disposition"]
    assert c.get(f"/api/empleados/{ctx['ids']['luis']}/certificado-antiguedad", headers=ctx["paula"]).status_code == 403
    assert c.get(f"/api/empleados/{ctx['ids']['luis']}/certificado-antiguedad", headers=ctx["admin"]).status_code == 200


# ---- panel y empleados ----------------------------------------------------------------

def test_panel_entrega_serie_por_area_y_comparacion_anual(ctx):
    r = ctx["c"].get("/api/dashboard/resumen", headers=ctx["admin"]).json()
    assert r["dotacion"] == 3 and r["dotacion_hace_un_anio"] == 3
    serie = r["serie"]
    assert len(serie["meses"]) == 12
    assert serie["areas"][0]["valores"][-1] == 3


def test_empleado_inactivo_guarda_fecha_de_salida_y_pierde_acceso(ctx):
    c, e = ctx["c"], ctx["ids"]["luis"]
    r = c.patch(f"/api/empleados/{e}", headers=ctx["admin"], json={"estado": "inactivo"}).json()
    assert r["fecha_salida"] == hoy().isoformat() and r["grupo"] == "A" and r["centro"] == "Planta Puerto Montt"
    volver = c.patch(f"/api/empleados/{e}", headers=ctx["admin"], json={"estado": "activo"}).json()
    assert volver["fecha_salida"] is None
