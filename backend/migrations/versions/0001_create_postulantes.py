"""Create postulantes table.

Revision ID: 0001_postulantes
Revises:
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_postulantes"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "postulantes",
        sa.Column("id_postulante", sa.Integer(), primary_key=True),
        sa.Column("nombres", sa.String(length=100), nullable=False),
        sa.Column("apellidos", sa.String(length=100), nullable=False),
        sa.Column("correo", sa.String(length=150), nullable=False),
        sa.Column("telefono", sa.String(length=20), nullable=True),
        sa.Column("cargo_postulado", sa.String(length=100), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default="recibido",
        ),
        sa.Column("cv_nombre_original", sa.String(length=255), nullable=False),
        sa.Column("cv_archivo", sa.String(length=255), nullable=False),
        sa.Column(
            "fecha_postulacion",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "estado IN ('recibido', 'en revisión', 'entrevista', 'contratado', 'rechazado')",
            name="postulantes_estado_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("postulantes")
