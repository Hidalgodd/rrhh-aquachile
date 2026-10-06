from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "rol IN ('admin', 'rrhh', 'empleado')",
            name="usuarios_rol_check",
        ),
    )

    id_usuario: Mapped[int] = mapped_column(primary_key=True)
    id_empleado: Mapped[int] = mapped_column(
        ForeignKey("empleados.id_empleado", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="empleado",
        server_default="empleado",
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
