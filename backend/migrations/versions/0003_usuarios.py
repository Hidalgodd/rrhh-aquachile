"""Create internal user accounts.

Revision ID: 0003_usuarios
Revises: 0002_empleados
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_usuarios"
down_revision: Union[str, None] = "0002_empleados"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id_usuario", sa.Integer(), primary_key=True),
        sa.Column("id_empleado", sa.Integer(), nullable=False, unique=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False, server_default="empleado"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["id_empleado"],
            ["empleados.id_empleado"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "rol IN ('admin', 'rrhh', 'empleado')",
            name="usuarios_rol_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
