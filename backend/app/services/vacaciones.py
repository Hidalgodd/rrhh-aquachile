from datetime import timedelta

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models.empleado import Empleado
from app.models.rrhh import Permiso, Turno
from app.services.calendario import dias_habiles
from app.services.turnos import trabaja
from app.tiempo import hoy

DIAS_ANUALES = 15  # Código del Trabajo: 15 días hábiles de feriado al año

TIPOS = {
    "vacaciones": "Vacaciones",
    "licencia medica": "Licencia médica",
    "administrativo": "Permiso administrativo",
}


def saldo(db: Session, id_empleado: int, anio: int | None = None) -> dict:
    """Cupo anual, días usados (aprobados) y en trámite (pendientes) de vacaciones."""
    anio = anio or hoy().year

    def suma(estado: str) -> int:
        return int(
            db.query(func.coalesce(func.sum(Permiso.dias), 0))
            .filter(
                Permiso.id_empleado == id_empleado,
                Permiso.tipo == "vacaciones",
                Permiso.estado == estado,
                extract("year", Permiso.fecha_inicio) == anio,
            )
            .scalar()
        )

    usados, en_tramite = suma("aprobado"), suma("pendiente")
    return {
        "cupo": DIAS_ANUALES,
        "usados": usados,
        "en_tramite": en_tramite,
        "disponibles": DIAS_ANUALES - usados,
        "libres": DIAS_ANUALES - usados - en_tramite,  # lo que aún se puede pedir
    }


def validar_solicitud(db: Session, empleado: Empleado, tipo: str, desde, hasta) -> dict:
    """Reglas de una solicitud. Lanza ValueError con un mensaje legible si no se puede."""
    if hasta < desde:
        raise ValueError("La fecha de término no puede ser anterior al inicio")
    if tipo != "licencia medica" and desde < hoy():
        raise ValueError("No puedes pedir días que ya pasaron")

    dias = dias_habiles(desde, hasta)
    if dias == 0:
        raise ValueError("Ese rango no incluye días hábiles")

    choque = (
        db.query(Permiso.id_permiso)
        .filter(
            Permiso.id_empleado == empleado.id_empleado,
            Permiso.estado.in_(["pendiente", "aprobado"]),
            Permiso.fecha_inicio <= hasta,
            Permiso.fecha_termino >= desde,
        )
        .first()
    )
    if choque:
        raise ValueError("Ya tienes una solicitud que se cruza con esas fechas")

    s = saldo(db, empleado.id_empleado, desde.year)
    if tipo == "vacaciones" and dias > s["libres"]:
        raise ValueError(
            f"No te alcanzan los días: pides {dias} y te quedan {max(s['libres'], 0)} "
            "libres descontando lo que está en trámite"
        )

    regimen, cruce = None, 0
    if empleado.id_turno:
        turno = db.get(Turno, empleado.id_turno)
        if turno:
            regimen = turno.regimen
            cruce = sum(
                1
                for i in range((hasta - desde).days + 1)
                if trabaja(turno.regimen, turno.fecha_ancla, desde + timedelta(i))
            )
    return {
        "dias": dias,
        "saldo_actual": s["disponibles"],
        "saldo_quedaria": s["disponibles"] - dias if tipo == "vacaciones" else s["disponibles"],
        "regimen": regimen,
        "dias_de_turno": cruce,
    }
