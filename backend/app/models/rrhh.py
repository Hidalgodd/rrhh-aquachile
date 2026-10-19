from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Centro(Base):
    """Planta o centro de cultivo donde trabajan los turnos."""

    __tablename__ = "centros"
    __table_args__ = (
        CheckConstraint("tipo IN ('planta', 'centro')", name="centros_tipo_check"),
    )

    id_centro: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="centro")


class Turno(Base):
    """Grupo de un centro con su régimen (7x7 o 14x14).

    `fecha_ancla` es el primer día de un bloque de trabajo del grupo; desde ahí
    se calcula todo el calendario (trabaja N días, descansa N días).
    """

    __tablename__ = "turnos"
    __table_args__ = (
        UniqueConstraint("id_centro", "grupo", "regimen", name="turnos_centro_grupo_uq"),
        CheckConstraint("grupo IN ('A', 'B')", name="turnos_grupo_check"),
        CheckConstraint("regimen IN ('7x7', '14x14')", name="turnos_regimen_check"),
    )

    id_turno: Mapped[int] = mapped_column(primary_key=True)
    id_centro: Mapped[int] = mapped_column(ForeignKey("centros.id_centro"), nullable=False)
    grupo: Mapped[str] = mapped_column(String(1), nullable=False)
    regimen: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_ancla: Mapped[date] = mapped_column(Date, nullable=False)


class Contrato(Base):
    __tablename__ = "contratos"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('indefinido', 'plazo fijo', 'por obra', 'honorarios')",
            name="contratos_tipo_check",
        ),
        CheckConstraint(
            "renovacion IN ('pendiente', 'renovado', 'no_renovar')",
            name="contratos_renovacion_check",
        ),
        CheckConstraint("sueldo >= 0", name="contratos_sueldo_check"),
    )

    id_contrato: Mapped[int] = mapped_column(primary_key=True)
    id_empleado: Mapped[int] = mapped_column(
        ForeignKey("empleados.id_empleado", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    titulo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    sueldo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    renovacion: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pendiente", server_default="pendiente"
    )


class Asistencia(Base):
    __tablename__ = "asistencias"
    __table_args__ = (
        UniqueConstraint("id_empleado", "fecha", name="asistencias_empleado_fecha_uq"),
    )

    id_asistencia: Mapped[int] = mapped_column(primary_key=True)
    id_empleado: Mapped[int] = mapped_column(
        ForeignKey("empleados.id_empleado", ondelete="CASCADE"), nullable=False
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    hora_entrada: Mapped[time | None] = mapped_column(Time, nullable=True)
    hora_salida: Mapped[time | None] = mapped_column(Time, nullable=True)


class Permiso(Base):
    __tablename__ = "permisos"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('vacaciones', 'licencia medica', 'administrativo')",
            name="permisos_tipo_check",
        ),
        CheckConstraint(
            "estado IN ('pendiente', 'aprobado', 'rechazado')",
            name="permisos_estado_check",
        ),
        CheckConstraint("fecha_termino >= fecha_inicio", name="permisos_fechas_check"),
    )

    id_permiso: Mapped[int] = mapped_column(primary_key=True)
    id_empleado: Mapped[int] = mapped_column(
        ForeignKey("empleados.id_empleado", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_termino: Mapped[date] = mapped_column(Date, nullable=False)
    dias: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pendiente", server_default="pendiente"
    )
    fecha_solicitud: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=func.now()
    )
    comentario_respuesta: Mapped[str | None] = mapped_column(String(500), nullable=True)
    id_resuelto_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id_usuario", ondelete="SET NULL"), nullable=True
    )
    fecha_respuesta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Documento(Base):
    __tablename__ = "documentos"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('contrato', 'anexo', 'liquidacion', 'identidad', 'otro')",
            name="documentos_tipo_check",
        ),
        CheckConstraint(
            "estado IN ('firmado', 'pendiente_firma', 'disponible', 'al_dia')",
            name="documentos_estado_check",
        ),
    )

    id_documento: Mapped[int] = mapped_column(primary_key=True)
    id_empleado: Mapped[int] = mapped_column(
        ForeignKey("empleados.id_empleado", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_firma: Mapped[date | None] = mapped_column(Date, nullable=True)
    archivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    archivo_original: Mapped[str | None] = mapped_column(String(255), nullable=True)
