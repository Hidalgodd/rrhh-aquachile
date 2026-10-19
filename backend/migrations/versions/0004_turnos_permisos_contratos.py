"""Centros, turnos, contratos, asistencias, permisos y documentos.

Funciona en una base nueva y también en una creada con el script SQL de
desarrollo (que ya traía contratos, asistencias y permisos con menos columnas).

Revision ID: 0004_turnos_permisos
Revises: 0003_usuarios
Create Date: 2026-10-16
"""
from datetime import date, timedelta
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_turnos_permisos"
down_revision: Union[str, None] = "0003_usuarios"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tablas() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columnas(tabla: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(tabla)}


def _recrear_check(tabla: str, nombre: str, condicion: str) -> None:
    """Cambia un CHECK existente (solo PostgreSQL; en SQLite el CHECK nace con la tabla)."""
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"ALTER TABLE {tabla} DROP CONSTRAINT IF EXISTS {nombre}")
    op.execute(f"ALTER TABLE {tabla} ADD CONSTRAINT {nombre} CHECK ({condicion})")


def _dias_habiles(desde: date, hasta: date) -> int:
    from app.services.calendario import dias_habiles

    return dias_habiles(desde, hasta)


def upgrade() -> None:
    existentes = _tablas()

    # --- centros y turnos --------------------------------------------------
    op.create_table(
        "centros",
        sa.Column("id_centro", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(100), nullable=False, unique=True),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="centro"),
        sa.CheckConstraint("tipo IN ('planta', 'centro')", name="centros_tipo_check"),
    )
    op.create_table(
        "turnos",
        sa.Column("id_turno", sa.Integer(), primary_key=True),
        sa.Column("id_centro", sa.Integer(), sa.ForeignKey("centros.id_centro"), nullable=False),
        sa.Column("grupo", sa.String(1), nullable=False),
        sa.Column("regimen", sa.String(10), nullable=False),
        sa.Column("fecha_ancla", sa.Date(), nullable=False),
        sa.UniqueConstraint("id_centro", "grupo", "regimen", name="turnos_centro_grupo_uq"),
        sa.CheckConstraint("grupo IN ('A', 'B')", name="turnos_grupo_check"),
        sa.CheckConstraint("regimen IN ('7x7', '14x14')", name="turnos_regimen_check"),
    )

    # --- empleados: turno y fecha de salida ----------------------------------
    op.add_column("empleados", sa.Column("id_turno", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "empleados_id_turno_fkey", "empleados", "turnos", ["id_turno"], ["id_turno"],
        ondelete="SET NULL",
    )
    op.add_column("empleados", sa.Column("fecha_salida", sa.Date(), nullable=True))
    op.execute(
        "UPDATE empleados SET fecha_salida = fecha_ingreso WHERE estado = 'inactivo' AND fecha_salida IS NULL"
    )

    # --- contratos -------------------------------------------------------------
    cond_tipo_contrato = "tipo IN ('indefinido', 'plazo fijo', 'por obra', 'honorarios')"
    if "contratos" in existentes:
        cols = _columnas("contratos")
        if "titulo" not in cols:
            op.add_column("contratos", sa.Column("titulo", sa.String(100), nullable=True))
        if "renovacion" not in cols:
            op.add_column(
                "contratos",
                sa.Column("renovacion", sa.String(20), nullable=False, server_default="pendiente"),
            )
            _recrear_check(
                "contratos", "contratos_renovacion_check",
                "renovacion IN ('pendiente', 'renovado', 'no_renovar')",
            )
        _recrear_check("contratos", "contratos_tipo_check", cond_tipo_contrato)
    else:
        op.create_table(
            "contratos",
            sa.Column("id_contrato", sa.Integer(), primary_key=True),
            sa.Column(
                "id_empleado", sa.Integer(),
                sa.ForeignKey("empleados.id_empleado", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("tipo", sa.String(30), nullable=False),
            sa.Column("titulo", sa.String(100)),
            sa.Column("fecha_inicio", sa.Date(), nullable=False),
            sa.Column("fecha_fin", sa.Date()),
            sa.Column("sueldo", sa.Numeric(10, 2), nullable=False),
            sa.Column("renovacion", sa.String(20), nullable=False, server_default="pendiente"),
            sa.CheckConstraint(cond_tipo_contrato, name="contratos_tipo_check"),
            sa.CheckConstraint(
                "renovacion IN ('pendiente', 'renovado', 'no_renovar')",
                name="contratos_renovacion_check",
            ),
            sa.CheckConstraint("sueldo >= 0", name="contratos_sueldo_check"),
            sa.CheckConstraint(
                "fecha_fin IS NULL OR fecha_fin >= fecha_inicio", name="contratos_fechas_check"
            ),
        )

    # --- asistencias -----------------------------------------------------------
    if "asistencias" not in existentes:
        op.create_table(
            "asistencias",
            sa.Column("id_asistencia", sa.Integer(), primary_key=True),
            sa.Column(
                "id_empleado", sa.Integer(),
                sa.ForeignKey("empleados.id_empleado", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("fecha", sa.Date(), nullable=False),
            sa.Column("hora_entrada", sa.Time()),
            sa.Column("hora_salida", sa.Time()),
            sa.UniqueConstraint("id_empleado", "fecha", name="asistencias_empleado_fecha_uq"),
        )

    # --- permisos --------------------------------------------------------------
    if "permisos" in existentes:
        cols = _columnas("permisos")
        if "dias" not in cols:
            op.add_column("permisos", sa.Column("dias", sa.Integer(), nullable=False, server_default="0"))
            filas = op.get_bind().execute(
                sa.text("SELECT id_permiso, fecha_inicio, fecha_termino FROM permisos")
            ).fetchall()
            for id_, ini, fin in filas:
                op.get_bind().execute(
                    sa.text("UPDATE permisos SET dias = :d WHERE id_permiso = :i"),
                    {"d": _dias_habiles(ini, fin), "i": id_},
                )
        if "fecha_solicitud" not in cols:
            op.add_column(
                "permisos",
                sa.Column("fecha_solicitud", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            )
        if "comentario_respuesta" not in cols:
            op.add_column("permisos", sa.Column("comentario_respuesta", sa.String(500)))
        if "id_resuelto_por" not in cols:
            op.add_column("permisos", sa.Column("id_resuelto_por", sa.Integer()))
            op.create_foreign_key(
                "permisos_id_resuelto_por_fkey", "permisos", "usuarios",
                ["id_resuelto_por"], ["id_usuario"], ondelete="SET NULL",
            )
        if "fecha_respuesta" not in cols:
            op.add_column("permisos", sa.Column("fecha_respuesta", sa.DateTime()))
    else:
        op.create_table(
            "permisos",
            sa.Column("id_permiso", sa.Integer(), primary_key=True),
            sa.Column(
                "id_empleado", sa.Integer(),
                sa.ForeignKey("empleados.id_empleado", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("tipo", sa.String(30), nullable=False),
            sa.Column("fecha_inicio", sa.Date(), nullable=False),
            sa.Column("fecha_termino", sa.Date(), nullable=False),
            sa.Column("dias", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
            sa.Column("fecha_solicitud", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("comentario_respuesta", sa.String(500)),
            sa.Column(
                "id_resuelto_por", sa.Integer(),
                sa.ForeignKey("usuarios.id_usuario", ondelete="SET NULL"),
            ),
            sa.Column("fecha_respuesta", sa.DateTime()),
            sa.CheckConstraint(
                "tipo IN ('vacaciones', 'licencia medica', 'administrativo')",
                name="permisos_tipo_check",
            ),
            sa.CheckConstraint(
                "estado IN ('pendiente', 'aprobado', 'rechazado')", name="permisos_estado_check"
            ),
            sa.CheckConstraint("fecha_termino >= fecha_inicio", name="permisos_fechas_check"),
        )

    # --- documentos ------------------------------------------------------------
    op.create_table(
        "documentos",
        sa.Column("id_documento", sa.Integer(), primary_key=True),
        sa.Column(
            "id_empleado", sa.Integer(),
            sa.ForeignKey("empleados.id_empleado", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("titulo", sa.String(150), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_firma", sa.Date()),
        sa.Column("archivo", sa.String(255)),
        sa.Column("archivo_original", sa.String(255)),
        sa.CheckConstraint(
            "tipo IN ('contrato', 'anexo', 'liquidacion', 'identidad', 'otro')",
            name="documentos_tipo_check",
        ),
        sa.CheckConstraint(
            "estado IN ('firmado', 'pendiente_firma', 'disponible', 'al_dia')",
            name="documentos_estado_check",
        ),
    )

    # Índices para las consultas más frecuentes
    op.create_index("ix_permisos_empleado_fechas", "permisos", ["id_empleado", "fecha_inicio"])
    op.create_index("ix_permisos_estado", "permisos", ["estado"])
    op.create_index("ix_empleados_turno", "empleados", ["id_turno"])
    op.create_index("ix_documentos_empleado", "documentos", ["id_empleado"])
    op.create_index("ix_contratos_empleado", "contratos", ["id_empleado"])


def downgrade() -> None:
    op.drop_index("ix_contratos_empleado", table_name="contratos")
    op.drop_index("ix_documentos_empleado", table_name="documentos")
    op.drop_index("ix_empleados_turno", table_name="empleados")
    op.drop_index("ix_permisos_estado", table_name="permisos")
    op.drop_index("ix_permisos_empleado_fechas", table_name="permisos")
    op.drop_table("documentos")
    op.drop_table("permisos")
    op.drop_table("asistencias")
    op.drop_table("contratos")
    op.drop_constraint("empleados_id_turno_fkey", "empleados", type_="foreignkey")
    op.drop_column("empleados", "fecha_salida")
    op.drop_column("empleados", "id_turno")
    op.drop_table("turnos")
    op.drop_table("centros")
