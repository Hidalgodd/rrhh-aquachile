"""Datos de demostración con las cifras del prototipo (248 personas, 6 áreas, 12 solicitudes...).

Uso (desde backend/, con la base ya migrada):
    python -m app.seed_demo            # solo si la base está vacía
    python -m app.seed_demo --reset    # BORRA todo y vuelve a cargar (solo desarrollo)

Todas las fechas se calculan respecto a hoy, así el panel y los turnos siempre se ven vivos.
"""
import argparse
import getpass
import random
import unicodedata
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models.empleado import Area, Cargo, Empleado
from app.models.postulante import Postulante
from app.models.rrhh import Asistencia, Centro, Contrato, Documento, Permiso, Turno
from app.models.usuario import Usuario
from app.security import hash_password
from app.services.calendario import dias_habiles, es_habil
from app.services.turnos import trabaja
from app.tiempo import hoy

RAIZ = Path(__file__).resolve().parents[1]
rnd = random.Random(2026)

# área -> (personas activas, [(cargo, sueldo, peso)])
AREAS = {
    "Procesamiento": (96, [("Operaria de planta", 650000, 0), ("Operario de planta", 650000, 0),
                           ("Supervisor de línea", 920000, 8), ("Técnico de procesamiento", 780000, 12)]),
    "Producción (centros)": (74, [("Jefe de turno", 1200000, 8), ("Supervisora de cultivo", 1100000, 6),
                                  ("Operario de centro", 780000, 56), ("Técnico acuícola", 840000, 30)]),
    "Logística": (31, [("Bodeguero", 700000, 40), ("Conductor", 720000, 40), ("Coordinador de logística", 1000000, 20)]),
    "Mantención": (22, [("Técnico mecánico", 850000, 45), ("Electricista", 880000, 40), ("Jefe de mantención", 1300000, 15)]),
    "Administración": (15, [("Analista de RRHH", 900000, 30), ("Contador", 1100000, 25),
                            ("Asistente administrativo", 700000, 35), ("Jefa de personas", 1500000, 10)]),
    "Calidad": (10, [("Analista de calidad", 950000, 60), ("Inspector de calidad", 800000, 40)]),
}
SALIDAS = {"Procesamiento": 4, "Producción (centros)": 4, "Logística": 2, "Mantención": 2,
           "Administración": 1, "Calidad": 1}  # 14 personas que se fueron en el último año

NOMBRES_F = ["Camila", "Javiera", "Constanza", "Fernanda", "Catalina", "Francisca", "Antonia", "Daniela", "Carolina",
             "Macarena", "Valeria", "Paulina", "Sofía", "Isidora", "Karen", "Pamela", "Nicole", "Bárbara", "Romina", "Yesenia"]
NOMBRES_M = ["Matías", "Benjamín", "Sebastián", "Cristóbal", "Nicolás", "Felipe", "Joaquín", "Ignacio", "Claudio",
             "Rodrigo", "Patricio", "Jorge", "Héctor", "Mauricio", "Gonzalo", "Esteban", "Ricardo", "Álvaro", "Fabián", "Óscar"]
APELLIDOS = ["González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva", "Martínez", "Sepúlveda", "Morales",
             "Rodríguez", "López", "Fuentes", "Hernández", "Torres", "Araya", "Flores", "Espinoza", "Valenzuela", "Castillo",
             "Tapia", "Reyes", "Gutiérrez", "Castro", "Pizarro", "Álvarez", "Vásquez", "Sánchez", "Fernández", "Ramírez",
             "Carrasco", "Gómez", "Cortés", "Herrera", "Núñez", "Jara", "Vergara", "Rivera", "Figueroa", "Riquelme", "García",
             "Miranda", "Bravo", "Vera", "Molina", "Vega", "Campos", "Sandoval", "Orellana", "Cárcamo", "Oyarzún", "Barría",
             "Alvarado", "Mansilla", "Aguilar", "Cárdenas", "Aravena", "Vidal", "Hidalgo"]
CALLES = ["Av. Costanera", "Av. Décima Región", "Calle Urmeneta", "Av. Diego Portales", "Calle San Felipe", "Av. Presidente Ibáñez"]


def dv(cuerpo: int) -> str:
    total = sum(int(d) * ((i % 6) + 2) for i, d in enumerate(reversed(str(cuerpo))))
    r = 11 - total % 11
    return "0" if r == 11 else "K" if r == 10 else str(r)


def sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def pdf_simple(titulo: str, lineas: list[str]) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2.5 * cm, 26 * cm, titulo)
    c.setFont("Helvetica", 11)
    y = 24.5 * cm
    for linea in lineas + ["", "Documento de demostración generado por el seed."]:
        c.drawString(2.5 * cm, y, linea)
        y -= 0.7 * cm
    c.save()
    return buf.getvalue()


def guardar_pdf(carpeta: str, titulo: str, lineas: list[str]) -> str:
    destino = RAIZ / "uploads" / carpeta
    destino.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid.uuid4().hex}.pdf"
    (destino / nombre).write_bytes(pdf_simple(titulo, lineas))
    return nombre


def siguiente_habil(d: date) -> date:
    d += timedelta(days=1)
    while not es_habil(d):
        d += timedelta(days=1)
    return d


def limpiar(db) -> None:
    tablas = ("documentos, permisos, asistencias, contratos, usuarios, empleados, "
              "turnos, centros, cargos, areas, postulantes")
    if engine.dialect.name == "postgresql":
        db.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))
    else:
        for t in tablas.split(", "):
            db.execute(text(f"DELETE FROM {t}"))
    db.commit()


def main() -> None:
    ap = argparse.ArgumentParser(description="Carga datos de demostración.")
    ap.add_argument("--reset", action="store_true", help="borra todo antes de cargar (solo desarrollo)")
    ap.add_argument("--password", help="contraseña de las cuentas de demo (mínimo 12 caracteres)")
    args = ap.parse_args()

    password = args.password or getpass.getpass("Contraseña para las cuentas de demo (mínimo 12 caracteres): ")
    if len(password) < 12:
        raise SystemExit("La contraseña debe tener al menos 12 caracteres.")

    hoy_ = hoy()
    lunes = hoy_ - timedelta(days=hoy_.weekday())
    proximo_lunes = lunes + timedelta(days=7)
    inicio_mes = hoy_.replace(day=1)
    corte_anio = hoy_ - timedelta(days=365)

    with SessionLocal() as db:
        if args.reset:
            limpiar(db)
        elif db.query(Empleado).count():
            raise SystemExit("La base ya tiene empleados. Usa --reset para reemplazarlos (borra todo).")

        # ---- áreas, cargos, centros y turnos ----------------------------------------
        areas: dict[str, Area] = {}
        cargos: dict[str, Cargo] = {}
        for nombre_area, (_, lista) in AREAS.items():
            areas[nombre_area] = Area(nombre=nombre_area)
            db.add(areas[nombre_area])
            db.flush()
            for nombre_cargo, sueldo, _p in lista:
                cargos[nombre_cargo] = Cargo(nombre=nombre_cargo, id_area=areas[nombre_area].id_area,
                                             sueldo_base=Decimal(sueldo))
                db.add(cargos[nombre_cargo])
        centros = {n: Centro(nombre=n, tipo=t) for n, t in
                   [("Planta Puerto Montt", "planta"), ("Centro Calbuco", "centro"), ("Centro Quellón", "centro")]}
        db.add_all(centros.values())
        db.flush()

        def turno(centro: str, grupo: str, regimen: str, ancla: date) -> Turno:
            t = Turno(id_centro=centros[centro].id_centro, grupo=grupo, regimen=regimen, fecha_ancla=ancla)
            db.add(t)
            return t

        # A trabaja el primer bloque; B, el siguiente. (El ancla es el primer día del bloque.)
        turnos = {
            "PM-A": turno("Planta Puerto Montt", "A", "7x7", lunes),
            "PM-B": turno("Planta Puerto Montt", "B", "7x7", lunes + timedelta(7)),
            "CA-A": turno("Centro Calbuco", "A", "7x7", lunes + timedelta(3)),
            "CA-B": turno("Centro Calbuco", "B", "7x7", lunes + timedelta(10)),
            "QU-A": turno("Centro Quellón", "A", "7x7", lunes - timedelta(3)),
            "QU-B": turno("Centro Quellón", "B", "7x7", lunes + timedelta(4)),
            "CA14-A": turno("Centro Calbuco", "A", "14x14", lunes - timedelta(7)),
            "CA14-B": turno("Centro Calbuco", "B", "14x14", lunes + timedelta(7)),
        }
        db.flush()

        # ---- personas ----------------------------------------------------------------
        usados_rut: set[int] = set()
        usados_correo: set[str] = set()

        def rut_para(cuerpo: int | None = None) -> str:
            while cuerpo is None or cuerpo in usados_rut:
                cuerpo = rnd.randint(9_000_000, 24_000_000)
            usados_rut.add(cuerpo)
            return f"{cuerpo}-{dv(cuerpo)}"

        def correo_para(nombre: str, apellido: str) -> str:
            base = f"{sin_tildes(nombre.split()[0])}.{sin_tildes(apellido.split()[0])}"
            correo, n = f"{base}@aquachile.cl", 1
            while correo in usados_correo:
                n += 1
                correo = f"{base}{n}@aquachile.cl"
            usados_correo.add(correo)
            return correo

        personas: list[dict] = []  # lo que luego se convierte en Empleado

        def agregar(**kw) -> dict:
            d = {"estado": "activo", "salida": None, "fijo": False, "usuario": None, "rol": "empleado", "turno": None}
            d.update(kw)
            personas.append(d)
            return d

        def nombrada(nombres, apellidos, cuerpo, area, cargo, ingreso, **kw):
            return agregar(
                nombres=nombres, apellidos=apellidos, rut=rut_para(cuerpo), area=area, cargo=cargo,
                ingreso=ingreso, correo=correo_para(nombres, apellidos.split()[0]) if "correo" not in kw else kw.pop("correo"),
                fijo=True, **kw)

        camila = nombrada("Camila", "Rojas Fuentes", 15_876_321, "Administración", "Analista de RRHH",
                          date(2019, 5, 6), usuario="admin", rol="admin")
        paula = nombrada("Paula", "Aguilar Mansilla", 12_345_678, "Procesamiento", "Operaria de planta",
                         date(2021, 3, 3), usuario="paula.aguilar", turno="PM-A", nacimiento=date(1994, 2, 14),
                         correo="paula.aguilar@aquachile.cl", telefono="+56 9 8765 4321",
                         direccion="Av. Costanera 1450, Puerto Montt")
        diego = nombrada("Diego", "Aravena Soto", 18_222_431, "Procesamiento", "Operario de planta",
                         inicio_mes + timedelta(days=min(2, (hoy_ - inicio_mes).days)), usuario="diego.aravena", turno="PM-A")
        luis = nombrada("Luis", "Díaz Gómez", 16_789_012, "Producción (centros)", "Jefe de turno",
                        date(2018, 1, 15), usuario="luis.diaz", turno="PM-A")
        ana = nombrada("Ana", "Cárdenas Vera", 15_444_555, "Producción (centros)", "Supervisora de cultivo",
                       date(2019, 7, 1), usuario="ana.cardenas", turno="QU-A", estado="licencia")
        valentina = nombrada("Valentina", "Núñez Alvarado", 17_654_321, "Calidad", "Analista de calidad",
                             inicio_mes + timedelta(days=min(1, (hoy_ - inicio_mes).days)),
                             usuario="valentina.nunez", turno="PM-A")
        marcos = nombrada("Marcos", "Vidal Torres", 18_455_902, "Procesamiento", "Operario de planta",
                          date(2026, 4, 15), usuario="marcos.vidal", turno="PM-A")
        tomas = nombrada("Tomás", "Barría Oyarzún", 17_100_234, "Procesamiento", "Operario de planta",
                         date(2022, 8, 22), usuario="tomas.barria", turno="PM-A")
        nombradas = [camila, paula, diego, luis, ana, valentina, marcos, tomas]

        def elegir_cargo(area: str, mujer: bool) -> str:
            lista = AREAS[area][1]
            if area == "Procesamiento":
                r = rnd.random()
                if r < 0.8:
                    return "Operaria de planta" if mujer else "Operario de planta"
                return "Supervisor de línea" if r < 0.88 else "Técnico de procesamiento"
            return rnd.choices([c for c, _, _ in lista], weights=[p for _, _, p in lista])[0]

        def generica(area: str, estado="activo", ingreso=None, salida=None) -> dict:
            mujer = rnd.random() < 0.42
            nombres = rnd.choice(NOMBRES_F if mujer else NOMBRES_M)
            apellidos = f"{rnd.choice(APELLIDOS)} {rnd.choice(APELLIDOS)}"
            cargo = elegir_cargo(area, mujer)
            if area == "Producción (centros)" and mujer and cargo == "Jefe de turno":
                cargo = "Supervisora de cultivo"
            return agregar(
                nombres=nombres, apellidos=apellidos, rut=rut_para(), area=area, cargo=cargo,
                ingreso=ingreso, salida=salida, estado=estado,
                correo=correo_para(nombres, apellidos.split()[0]),
                telefono=f"+56 9 {rnd.randint(5000, 9999)} {rnd.randint(1000, 9999)}",
                direccion=f"{rnd.choice(CALLES)} {rnd.randint(100, 2900)}, Puerto Montt",
                nacimiento=date(rnd.randint(1968, 2003), rnd.randint(1, 12), rnd.randint(1, 28)))

        # Cuántos faltan por área (descontando las nombradas)
        faltan = {a: n for a, (n, _) in AREAS.items()}
        for p in nombradas:
            faltan[p["area"]] -= 1
        # Nuevos del año: 31 en total = 7 este mes + 24 en los 11 meses anteriores (Marcos es uno)
        nuevos_mes = 7 - sum(1 for p in nombradas if p["ingreso"] >= inicio_mes)
        nuevos_ano = 24 - sum(1 for p in nombradas if corte_anio < p["ingreso"] < inicio_mes)
        pool_areas = [a for a, n in faltan.items() for _ in range(n)]
        rnd.shuffle(pool_areas)
        for i, area in enumerate(pool_areas):
            if i < nuevos_mes:
                ing = inicio_mes + timedelta(days=rnd.randint(0, (hoy_ - inicio_mes).days))
            elif i < nuevos_mes + nuevos_ano:
                ing = hoy_ - timedelta(days=rnd.randint(40, 355))
                ing = min(ing, inicio_mes - timedelta(days=1))
            else:
                ing = hoy_ - timedelta(days=rnd.randint(380, 365 * 9))
            generica(area, ingreso=ing)
        for area, n in SALIDAS.items():  # quienes se fueron durante el año (siguen en la base como inactivos)
            for _ in range(n):
                generica(area, estado="inactivo", ingreso=hoy_ - timedelta(days=rnd.randint(420, 365 * 6)),
                         salida=hoy_ - timedelta(days=rnd.randint(8, 350)))

        # ---- asignación de turnos ---------------------------------------------------------
        vivos = [p for p in personas if p["estado"] != "inactivo" and not p["fijo"]]

        def llenar(clave: str, cantidad: int, area: str) -> None:
            ya = sum(1 for p in personas if p["turno"] == clave)
            candidatos = [p for p in vivos if p["area"] == area and p["turno"] is None]
            for p in rnd.sample(candidatos, cantidad - ya):
                p["turno"] = clave

        llenar("PM-A", 34, "Procesamiento")
        llenar("PM-B", 34, "Procesamiento")
        llenar("CA-A", 12, "Producción (centros)")
        llenar("CA-B", 12, "Producción (centros)")
        llenar("QU-A", 15, "Producción (centros)")
        llenar("QU-B", 15, "Producción (centros)")
        llenar("CA14-A", 4, "Mantención")
        llenar("CA14-B", 4, "Mantención")

        # 9 personas con licencia: Ana, 2 del grupo A de Puerto Montt y 6 más
        libres = [p for p in vivos if p["estado"] == "activo"]
        en_pm_a = [p for p in libres if p["turno"] == "PM-A"]
        elegidos = rnd.sample(en_pm_a, 2)
        resto = [p for p in libres if p not in elegidos]
        elegidos += rnd.sample(resto, 6)
        for p in elegidos:
            p["estado"] = "licencia"

        # ---- guardar empleados y cuentas ------------------------------------------------
        empleados: list[tuple[dict, Empleado]] = []
        for p in personas:
            e = Empleado(
                rut=p["rut"], nombres=p["nombres"], apellidos=p["apellidos"], correo=p["correo"],
                fecha_nacimiento=p.get("nacimiento"), telefono=p.get("telefono"), direccion=p.get("direccion"),
                fecha_ingreso=p["ingreso"], fecha_salida=p["salida"], estado=p["estado"],
                id_cargo=cargos[p["cargo"]].id_cargo,
                id_turno=turnos[p["turno"]].id_turno if p["turno"] else None)
            db.add(e)
            empleados.append((p, e))
        db.flush()

        clave = hash_password(password)
        for p, e in empleados:
            if p["usuario"]:
                db.add(Usuario(id_empleado=e.id_empleado, username=p["usuario"], password_hash=clave, rol=p["rol"]))
        db.flush()
        por_usuario = {p["usuario"]: e for p, e in empleados if p["usuario"]}

        # ---- contratos y documentos ---------------------------------------------------------
        for p, e in empleados:
            sueldo = cargos[p["cargo"]].sueldo_base
            if p["estado"] == "inactivo":
                db.add(Contrato(id_empleado=e.id_empleado, tipo="plazo fijo", fecha_inicio=p["ingreso"],
                                fecha_fin=p["salida"], sueldo=sueldo, renovacion="no_renovar"))
                continue
            if e is por_usuario["marcos.vidal"]:
                continue  # su historial se arma a mano más abajo
            reciente = p["ingreso"] > hoy_ - timedelta(days=365)
            if reciente or rnd.random() < 0.25:
                fin = hoy_ + timedelta(days=rnd.randint(40, 300))
                db.add(Contrato(id_empleado=e.id_empleado, tipo="plazo fijo", fecha_inicio=p["ingreso"],
                                fecha_fin=max(fin, p["ingreso"] + timedelta(days=90)), sueldo=sueldo))
            else:
                db.add(Contrato(id_empleado=e.id_empleado, tipo="indefinido", fecha_inicio=p["ingreso"], sueldo=sueldo))
            db.add(Documento(id_empleado=e.id_empleado, tipo="contrato", titulo="Contrato de trabajo",
                             estado="firmado", fecha_emision=p["ingreso"], fecha_firma=p["ingreso"]))

        m = por_usuario["marcos.vidal"]
        db.add(Contrato(id_empleado=m.id_empleado, tipo="honorarios", titulo="Honorarios de práctica",
                        fecha_inicio=date(2026, 1, 15), fecha_fin=date(2026, 4, 14), sueldo=Decimal(450000),
                        renovacion="renovado"))
        db.add(Contrato(id_empleado=m.id_empleado, tipo="plazo fijo", fecha_inicio=date(2026, 4, 15),
                        fecha_fin=hoy_ + timedelta(days=30), sueldo=Decimal(650000)))

        def doc(e: Empleado, tipo, titulo, estado, emision, firma=None, con_archivo=True):
            archivo = guardar_pdf("documentos", titulo, [f"Empleado: {e.nombres} {e.apellidos}", f"RUT: {e.rut}"]) \
                if con_archivo else None
            db.add(Documento(id_empleado=e.id_empleado, tipo=tipo, titulo=titulo, estado=estado, fecha_emision=emision,
                             fecha_firma=firma, archivo=archivo, archivo_original=f"{titulo}.pdf" if archivo else None))

        p_ = por_usuario["paula.aguilar"]
        doc(p_, "anexo", "Anexo de turno 7x7", "pendiente_firma", hoy_ - timedelta(days=6))
        doc(p_, "liquidacion", "Liquidación de septiembre", "disponible", date(hoy_.year, hoy_.month, 5))
        doc(m, "contrato", "Contrato de trabajo", "firmado", date(2026, 4, 15), firma=date(2026, 4, 15))
        doc(m, "anexo", "Anexo de turno 7x7", "pendiente_firma", hoy_ - timedelta(days=6))
        doc(m, "identidad", "Cédula de identidad", "al_dia", date(2026, 4, 15))
        # el contrato de Paula (ya creado arriba sin archivo) también debe poder abrirse
        db.flush()
        c_paula = db.query(Documento).filter(Documento.id_empleado == p_.id_empleado, Documento.tipo == "contrato").one()
        c_paula.archivo = guardar_pdf("documentos", "Contrato de trabajo", [f"Empleado: {p_.nombres} {p_.apellidos}"])
        c_paula.archivo_original = "Contrato de trabajo.pdf"

        # ---- permisos --------------------------------------------------------------------------
        def permiso(e: Empleado, tipo: str, ini: date, fin: date, estado: str, comentario=None, solicitado_hace=3):
            db.add(Permiso(id_empleado=e.id_empleado, tipo=tipo, fecha_inicio=ini, fecha_termino=fin,
                           dias=dias_habiles(ini, fin), estado=estado, comentario_respuesta=comentario,
                           fecha_solicitud=datetime.combine(hoy_ - timedelta(days=solicitado_hace), time(10, 0))))

        # historial de Paula: usó 4 días de vacaciones este año
        permiso(p_, "vacaciones", date(hoy_.year, 2, 13), date(hoy_.year, 2, 18), "aprobado", "Que descanses", 40)
        permiso(p_, "administrativo", date(hoy_.year, 9, 3), date(hoy_.year, 9, 3), "aprobado", None, 10)
        permiso(p_, "administrativo", date(hoy_.year, 1, 9), date(hoy_.year, 1, 9), "rechazado", "Faltaba personal ese día", 30)

        # 12 solicitudes pendientes
        permiso(p_, "vacaciones", proximo_lunes, proximo_lunes + timedelta(4), "pendiente", None, 1)
        permiso(por_usuario["diego.aravena"], "administrativo", siguiente_habil(hoy_), siguiente_habil(hoy_), "pendiente")
        permiso(por_usuario["luis.diaz"], "licencia medica", proximo_lunes, proximo_lunes + timedelta(7), "pendiente")
        permiso(por_usuario["valentina.nunez"], "vacaciones", proximo_lunes + timedelta(14), proximo_lunes + timedelta(18), "pendiente")
        permiso(m, "administrativo", proximo_lunes + timedelta(2), proximo_lunes + timedelta(2), "pendiente")
        otros = [e for p, e in empleados if not p["fijo"] and p["estado"] == "activo" and p["turno"]]
        for e, (tipo, dias_) in zip(rnd.sample(otros, 7),
                                    [("vacaciones", 5), ("administrativo", 1), ("vacaciones", 10), ("administrativo", 1),
                                     ("vacaciones", 5), ("vacaciones", 3), ("administrativo", 1)]):
            ini = proximo_lunes + timedelta(days=rnd.randint(0, 25))
            while not es_habil(ini):
                ini += timedelta(1)
            fin = ini
            while dias_habiles(ini, fin) < dias_:
                fin += timedelta(1)
            permiso(e, tipo, ini, fin, "pendiente", None, rnd.randint(0, 6))

        # ausencias ya aprobadas del grupo A (alimentan el cuadro «quiénes faltarán esa semana»)
        a_pm = [e for p, e in empleados if p["turno"] == "PM-A" and not p["fijo"] and p["estado"] == "activo"]
        for e, (d0, d1) in zip(a_pm, [(0, 4), (1, 3), (2, 2)]):
            permiso(e, "vacaciones", proximo_lunes + timedelta(d0), proximo_lunes + timedelta(d1), "aprobado")
        # y dos con vacaciones esta semana, para que la grilla de turnos muestre otra cosa que turno
        for e in a_pm[3:5]:
            permiso(e, "vacaciones", lunes + timedelta(3), lunes + timedelta(6), "aprobado")
        # licencias médicas vigentes de quienes están con licencia
        for p, e in empleados:
            if p["estado"] == "licencia":
                permiso(e, "licencia medica", hoy_ - timedelta(days=3), max(hoy_ + timedelta(days=1), lunes + timedelta(days=6)), "aprobado")

        # ---- asistencia ------------------------------------------------------------------------
        aus_hoy = {e.id_empleado for p, e in empleados if p["estado"] == "licencia"}
        fijas_hoy = {"paula.aguilar": time(7, 58), "diego.aravena": time(8, 2), "marcos.vidal": time(7, 49)}
        for p, e in empleados:
            if not p["turno"] or p["estado"] == "inactivo":
                continue
            t = turnos[p["turno"]]
            for atras in range(0, 21):
                dia = hoy_ - timedelta(days=atras)
                if dia < p["ingreso"] or not trabaja(t.regimen, t.fecha_ancla, dia) or e.id_empleado in aus_hoy:
                    continue
                if atras == 0:
                    if p["usuario"] == "tomas.barria":
                        continue
                    entrada = fijas_hoy.get(p["usuario"])
                    if entrada is None:
                        if rnd.random() > 0.83:
                            continue
                        entrada = time(7, rnd.randint(30, 59)) if rnd.random() < 0.8 else time(8, rnd.randint(0, 20))
                    db.add(Asistencia(id_empleado=e.id_empleado, fecha=dia, hora_entrada=entrada))
                elif rnd.random() < 0.94:
                    entrada = time(7, rnd.randint(35, 59))
                    salida = (datetime.combine(dia, entrada) + timedelta(hours=9, minutes=rnd.randint(0, 30))).time()
                    db.add(Asistencia(id_empleado=e.id_empleado, fecha=dia, hora_entrada=entrada, hora_salida=salida))

        # ---- postulantes -----------------------------------------------------------------------
        estados = ["recibido"] * 7 + ["en revisión"] * 5 + ["entrevista"] * 2 + ["contratado", "rechazado", "rechazado"]
        puestos = ["Operaria de planta", "Operario de centro", "Técnico acuícola", "Conductor", "Analista de calidad",
                   "Electricista", "Bodeguero", "Asistente administrativo"]
        for i, estado in enumerate(estados):
            mujer = rnd.random() < 0.5
            nom = rnd.choice(NOMBRES_F if mujer else NOMBRES_M)
            ape = f"{rnd.choice(APELLIDOS)} {rnd.choice(APELLIDOS)}"
            archivo = guardar_pdf("cvs", f"CV {nom} {ape}", [f"Postula a: {puestos[i % len(puestos)]}"])
            db.add(Postulante(
                nombres=nom, apellidos=ape, correo=f"{sin_tildes(nom)}.{sin_tildes(ape.split()[0])}{i}@correo.cl",
                telefono=f"+56 9 {rnd.randint(5000, 9999)} {rnd.randint(1000, 9999)}",
                cargo_postulado=puestos[i % len(puestos)], estado=estado, cv_nombre_original=f"CV {nom}.pdf",
                cv_archivo=archivo, fecha_postulacion=datetime.combine(hoy_ - timedelta(days=rnd.randint(0, 20)), time(11, 0))))

        db.commit()

    print("Datos de demostración cargados.")
    print("Cuentas (todas con la contraseña que ingresaste):")
    print("  admin           Camila Rojas, administración (panel, aprobaciones, turnos...)")
    print("  paula.aguilar   portal del colaborador")
    print("  marcos.vidal, diego.aravena, luis.diaz, ana.cardenas, valentina.nunez, tomas.barria")


if __name__ == "__main__":
    main()
