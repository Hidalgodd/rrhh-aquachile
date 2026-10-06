"""Create employee reference tables.

Revision ID: 0002_empleados
Revises: 0001_postulantes
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_empleados"
down_revision: Union[str, None] = "0001_postulantes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "areas",
        sa.Column("id_area", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=100), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(length=255)),
    )
    op.create_table(
        "cargos",
        sa.Column("id_cargo", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("id_area", sa.Integer(), nullable=False),
        sa.Column("sueldo_base", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["id_area"], ["areas.id_area"]),
        sa.CheckConstraint("sueldo_base >= 0", name="cargos_sueldo_base_check"),
    )
    op.create_table(
        "empleados",
        sa.Column("id_empleado", sa.Integer(), primary_key=True),
        sa.Column("rut", sa.String(length=12), nullable=False, unique=True),
        sa.Column("nombres", sa.String(length=100), nullable=False),
        sa.Column("apellidos", sa.String(length=100), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date()),
        sa.Column("correo", sa.String(length=150), nullable=False, unique=True),
        sa.Column("telefono", sa.String(length=20)),
        sa.Column("direccion", sa.String(length=200)),
        sa.Column("fecha_ingreso", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("id_cargo", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="activo"),
        sa.ForeignKeyConstraint(["id_cargo"], ["cargos.id_cargo"]),
        sa.CheckConstraint(
            "estado IN ('activo', 'inactivo', 'licencia')",
            name="empleados_estado_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("empleados")
    op.drop_table("cargos")
    op.drop_table("areas")
