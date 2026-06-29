"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contribuyentes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cuit", sa.String(11), nullable=False, unique=True),
        sa.Column("razon_social", sa.String(250), nullable=False),
        sa.Column("condicion_iva", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("domicilio", sa.String(500), nullable=True),
        sa.Column("localidad", sa.String(100), nullable=True),
        sa.Column("provincia", sa.String(100), nullable=True),
        sa.Column("codigo_postal", sa.String(10), nullable=True),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("categoria_fiscal", sa.String(50), nullable=True),
        sa.Column("ingresos_brutos", sa.String(50), nullable=True),
        sa.Column("es_cliente", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("es_proveedor", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("creado", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("actualizado", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_contribuyente_cuit", "contribuyentes", ["cuit"])
    op.create_index("idx_contribuyente_rs", "contribuyentes", ["razon_social"])

    op.create_table(
        "productos_servicios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False, unique=True),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="PRODUCTO"),
        sa.Column("precio_base", sa.Float(), nullable=False, server_default="0"),
        sa.Column("alicuota_iva", sa.Float(), nullable=False, server_default="21"),
        sa.Column("unidad_medida", sa.String(20), nullable=False, server_default="unidad"),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("creado", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("actualizado", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "facturas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uuid", sa.String(36), nullable=False, unique=True),
        sa.Column("tipo_comprobante", sa.Integer(), nullable=False),
        sa.Column("punto_venta", sa.Integer(), nullable=False),
        sa.Column("numero_factura", sa.Integer(), nullable=True),
        sa.Column("cae", sa.String(14), nullable=True),
        sa.Column("cae_vencimiento", sa.DateTime(), nullable=True),
        sa.Column("resultado", sa.String(20), nullable=True),
        sa.Column("fecha_emision", sa.DateTime(), nullable=False),
        sa.Column("fecha_vencimiento_pago", sa.Date(), nullable=True),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("contribuyentes.id"), nullable=False),
        sa.Column("cuit_cliente", sa.String(11), nullable=False),
        sa.Column("razon_social_cliente", sa.String(250), nullable=False),
        sa.Column("condicion_iva_cliente", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("domicilio_cliente", sa.String(500), nullable=True),
        sa.Column("concepto", sa.String(20), nullable=False, server_default="PRODUCTOS"),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("cotizacion", sa.Float(), nullable=False, server_default="1"),
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("iva_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("percepcion_iibb", sa.Float(), nullable=False, server_default="0"),
        sa.Column("percepcion_iva", sa.Float(), nullable=False, server_default="0"),
        sa.Column("otros_impuestos", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bonificacion", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="BORRADOR"),
        sa.Column("motivo_anulacion", sa.Text(), nullable=True),
        sa.Column("factura_origen_id", sa.Integer(), sa.ForeignKey("facturas.id"), nullable=True),
        sa.Column("cae_original", sa.String(14), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(20), nullable=True),
        sa.Column("xml_request", sa.Text(), nullable=True),
        sa.Column("xml_response", sa.Text(), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sync_status", sa.String(20), nullable=False, server_default="LOCAL"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "detalles_factura",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("factura_id", sa.Integer(), sa.ForeignKey("facturas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("producto_id", sa.Integer(), sa.ForeignKey("productos_servicios.id"), nullable=True),
        sa.Column("codigo_producto", sa.String(50), nullable=True),
        sa.Column("descripcion", sa.String(500), nullable=False),
        sa.Column("cantidad", sa.Float(), nullable=False, server_default="1"),
        sa.Column("unidad_medida", sa.String(20), nullable=False, server_default="unidad"),
        sa.Column("precio_unitario", sa.Float(), nullable=False, server_default="0"),
        sa.Column("alicuota_iva", sa.Float(), nullable=False, server_default="21"),
        sa.Column("importe_iva", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bonificacion", sa.Float(), nullable=False, server_default="0"),
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tokens_wsaa",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("sign", sa.Text(), nullable=False),
        sa.Column("expiration_time", sa.DateTime(), nullable=False),
        sa.Column("generation_time", sa.DateTime(), nullable=False),
        sa.Column("cuit", sa.String(11), nullable=False),
        sa.Column("certificate_hash", sa.String(64), nullable=True),
        sa.Column("encrypted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "auditoria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("usuario", sa.String(100), nullable=False, server_default="system"),
        sa.Column("accion", sa.String(100), nullable=False),
        sa.Column("entidad", sa.String(50), nullable=True),
        sa.Column("entidad_id", sa.Integer(), nullable=True),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("ip_origen", sa.String(50), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("nivel", sa.String(20), nullable=False, server_default="INFO"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "configuracion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("clave", sa.String(100), nullable=False, unique=True),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.Column("categoria", sa.String(50), nullable=False, server_default="general"),
        sa.Column("descripcion", sa.String(500), nullable=True),
        sa.Column("encriptado", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("actualizado", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "backups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="AUTOMATICO"),
        sa.Column("creado", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("restaurado", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_factura_fecha", "facturas", ["fecha_emision"])
    op.create_index("idx_factura_cae", "facturas", ["cae"])
    op.create_index("idx_factura_cuit_fecha", "facturas", ["cuit_cliente", "fecha_emision"])
    op.create_index("idx_factura_tipo_estado", "facturas", ["tipo_comprobante", "estado"])
    op.create_index("idx_factura_pv_numero", "facturas", ["punto_venta", "numero_factura"])
    op.create_index("idx_token_service", "tokens_wsaa", ["service"])
    op.create_index("idx_token_expiration", "tokens_wsaa", ["expiration_time"])
    op.create_index("idx_audit_timestamp_accion", "auditoria", ["timestamp", "accion"])


def downgrade() -> None:
    op.drop_table("detalles_factura")
    op.drop_table("facturas")
    op.drop_table("tokens_wsaa")
    op.drop_table("auditoria")
    op.drop_table("configuracion")
    op.drop_table("backups")
    op.drop_table("productos_servicios")
    op.drop_table("contribuyentes")
