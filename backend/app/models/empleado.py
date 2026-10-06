from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Area(Base):
    __tablename__ = "areas"

    id_area: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Cargo(Base):
    __tablename__ = "cargos"
    __table_args__ = (
        CheckConstraint("sueldo_base >= 0", name="cargos_sueldo_base_check"),
    )

    id_cargo: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    id_area: Mapped[int] = mapped_column(ForeignKey("areas.id_area"), nullable=False)
    sueldo_base: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)


class Empleado(Base):
    __tablename__ = "empleados"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('activo', 'inactivo', 'licencia')",
            name="empleados_estado_check",
        ),
    )

    id_empleado: Mapped[int] = mapped_column(primary_key=True)
    rut: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    correo: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fecha_ingreso: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=func.current_date(),
    )
    id_cargo: Mapped[int] = mapped_column(ForeignKey("cargos.id_cargo"), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activo")
