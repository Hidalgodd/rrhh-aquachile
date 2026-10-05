from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Postulante(Base):
    __tablename__ = "postulantes"

    id_postulante: Mapped[int] = mapped_column(primary_key=True)
    nombres: Mapped[str] = mapped_column(String(100))
    apellidos: Mapped[str] = mapped_column(String(100))
    correo: Mapped[str] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cargo_postulado: Mapped[str] = mapped_column(String(100))
    estado: Mapped[str] = mapped_column(String(20), default="recibido")
    cv_nombre_original: Mapped[str] = mapped_column(String(255))
    cv_archivo: Mapped[str] = mapped_column(String(255))  # nombre guardado en disco
    fecha_postulacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
