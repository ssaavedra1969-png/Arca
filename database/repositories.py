from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import scoped_session, joinedload
from sqlalchemy import func, or_, and_, desc, text

from database.models import (
    Contribuyente, ProductoServicio, Factura, DetalleFactura,
    TokenWSAA, Auditoria, Configuracion, Backup, EstadoFactura,
    TipoComprobante, Base
)
from utils.exceptions import (
    DatabaseError, IntegrityError, ValidationError
)
from loguru import logger


class ContribuyenteRepository:
    def __init__(self, session: scoped_session):
        self.session = session

    def get_by_id(self, id: int) -> Optional[Contribuyente]:
        return self.session.get(Contribuyente, id)

    def get_by_cuit(self, cuit: str) -> Optional[Contribuyente]:
        return self.session.query(Contribuyente).filter(
            Contribuyente.cuit == cuit
        ).first()

    def search(self, query: str, limit: int = 20) -> List[Contribuyente]:
        q = f"%{query}%"
        return self.session.query(Contribuyente).filter(
            or_(
                Contribuyente.cuit.like(q),
                Contribuyente.razon_social.like(q),
            )
        ).limit(limit).all()

    def list_all(self, activo: bool = True) -> List[Contribuyente]:
        return self.session.query(Contribuyente).filter(
            Contribuyente.activo == activo
        ).order_by(Contribuyente.razon_social).all()

    def create(self, data: Dict[str, Any]) -> Contribuyente:
        try:
            contribuyente = Contribuyente(**data)
            self.session.add(contribuyente)
            self.session.flush()
            logger.info(f"Contribuyente creado: {contribuyente.cuit} - {contribuyente.razon_social}")
            return contribuyente
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error creando contribuyente: {e}")

    def update(self, id: int, data: Dict[str, Any]) -> Contribuyente:
        contribuyente = self.get_by_id(id)
        if not contribuyente:
            raise DatabaseError(f"Contribuyente {id} no encontrado")
        try:
            for key, value in data.items():
                if hasattr(contribuyente, key):
                    setattr(contribuyente, key, value)
            self.session.flush()
            return contribuyente
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error actualizando contribuyente: {e}")

    def delete(self, id: int):
        contribuyente = self.get_by_id(id)
        if contribuyente:
            contribuyente.activo = False
            self.session.flush()

    def get_frecuentes(self, limit: int = 10) -> List[Tuple[Contribuyente, int]]:
        return self.session.query(
            Contribuyente, func.count(Factura.id).label("total")
        ).join(
            Factura, Factura.cliente_id == Contribuyente.id
        ).group_by(Contribuyente.id).order_by(
            desc("total")
        ).limit(limit).all()


class ProductoRepository:
    def __init__(self, session: scoped_session):
        self.session = session

    def get_by_id(self, id: int) -> Optional[ProductoServicio]:
        return self.session.get(ProductoServicio, id)

    def get_by_codigo(self, codigo: str) -> Optional[ProductoServicio]:
        return self.session.query(ProductoServicio).filter(
            ProductoServicio.codigo == codigo
        ).first()

    def search(self, query: str, limit: int = 20) -> List[ProductoServicio]:
        q = f"%{query}%"
        return self.session.query(ProductoServicio).filter(
            or_(
                ProductoServicio.codigo.like(q),
                ProductoServicio.descripcion.like(q),
            )
        ).limit(limit).all()

    def list_by_tipo(self, tipo: str) -> List[ProductoServicio]:
        return self.session.query(ProductoServicio).filter(
            ProductoServicio.tipo == tipo,
            ProductoServicio.activo == True,
        ).all()

    def create(self, data: Dict[str, Any]) -> ProductoServicio:
        try:
            prod = ProductoServicio(**data)
            self.session.add(prod)
            self.session.flush()
            return prod
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error creando producto: {e}")

    def update(self, id: int, data: Dict[str, Any]) -> ProductoServicio:
        prod = self.get_by_id(id)
        if not prod:
            raise DatabaseError(f"Producto {id} no encontrado")
        try:
            for key, value in data.items():
                if hasattr(prod, key):
                    setattr(prod, key, value)
            self.session.flush()
            return prod
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error actualizando producto: {e}")


class FacturaRepository:
    def __init__(self, session: scoped_session):
        self.session = session

    def get_by_id(self, id: int) -> Optional[Factura]:
        return self.session.query(Factura).options(
            joinedload(Factura.detalles),
            joinedload(Factura.cliente),
        ).filter(Factura.id == id).first()

    def get_by_uuid(self, uuid: str) -> Optional[Factura]:
        return self.session.query(Factura).filter(Factura.uuid == uuid).first()

    def get_by_cae(self, cae: str) -> Optional[Factura]:
        return self.session.query(Factura).filter(Factura.cae == cae).first()

    def get_ultimo_numero(self, punto_venta: int, tipo_comprobante: int) -> int:
        result = self.session.query(func.max(Factura.numero_factura)).filter(
            Factura.punto_venta == punto_venta,
            Factura.tipo_comprobante == tipo_comprobante,
        ).scalar()
        return result or 0

    def search(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> Tuple[List[Factura], int]:
        query = self.session.query(Factura)

        if filters.get("fecha_desde"):
            query = query.filter(Factura.fecha_emision >= filters["fecha_desde"])
        if filters.get("fecha_hasta"):
            query = query.filter(Factura.fecha_emision <= filters["fecha_hasta"])
        if filters.get("tipo_comprobante"):
            query = query.filter(Factura.tipo_comprobante == filters["tipo_comprobante"])
        if filters.get("estado"):
            query = query.filter(Factura.estado == filters["estado"])
        if filters.get("cuit_cliente"):
            query = query.filter(Factura.cuit_cliente.like(f"%{filters['cuit_cliente']}%"))
        if filters.get("razon_social"):
            query = query.filter(Factura.razon_social_cliente.like(f"%{filters['razon_social']}%"))
        if filters.get("punto_venta"):
            query = query.filter(Factura.punto_venta == filters["punto_venta"])
        if filters.get("cae"):
            query = query.filter(Factura.cae == filters["cae"])

        total = query.count()
        resultados = query.order_by(
            desc(Factura.fecha_emision)
        ).offset(offset).limit(limit).all()

        return resultados, total

    def create(self, data: Dict[str, Any], detalles: List[Dict[str, Any]]) -> Factura:
        try:
            factura = Factura(**data)
            self.session.add(factura)
            self.session.flush()

            for i, det in enumerate(detalles):
                det["factura_id"] = factura.id
                det["orden"] = i + 1
                detalle = DetalleFactura(**det)
                self.session.add(detalle)

            self.session.flush()
            factura = self._recalcular_totales(factura)
            logger.info(f"Factura creada: {factura.uuid}")
            return factura
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error creando factura: {e}")

    def update_estado(self, id: int, estado: str, **kwargs):
        factura = self.get_by_id(id)
        if not factura:
            raise DatabaseError(f"Factura {id} no encontrada")
        try:
            factura.estado = estado
            for key, value in kwargs.items():
                if hasattr(factura, key):
                    setattr(factura, key, value)
            self.session.flush()
            return factura
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error actualizando factura: {e}")

    def get_pendientes(self) -> List[Factura]:
        return self.session.query(Factura).filter(
            Factura.estado == EstadoFactura.PENDIENTE.value
        ).order_by(Factura.fecha_emision).all()

    def get_borradores(self) -> List[Factura]:
        return self.session.query(Factura).filter(
            Factura.estado == EstadoFactura.BORRADOR.value
        ).order_by(desc(Factura.updated_at)).all()

    def get_estadisticas(self, fecha_desde: Optional[date] = None, fecha_hasta: Optional[date] = None) -> Dict[str, Any]:
        if not fecha_hasta:
            fecha_hasta = date.today()
        if not fecha_desde:
            fecha_desde = fecha_hasta - timedelta(days=30)

        q = self.session.query(Factura).filter(
            Factura.fecha_emision >= fecha_desde,
            Factura.fecha_emision <= fecha_hasta,
            Factura.estado == EstadoFactura.EMITIDA.value,
        )

        total_facturado = q.with_entities(func.sum(Factura.total)).scalar() or 0
        cantidad_facturas = q.count()

        por_tipo = self.session.query(
            Factura.tipo_comprobante, func.count(Factura.id), func.sum(Factura.total)
        ).filter(
            Factura.fecha_emision >= fecha_desde,
            Factura.fecha_emision <= fecha_hasta,
            Factura.estado == EstadoFactura.EMITIDA.value,
        ).group_by(Factura.tipo_comprobante).all()

        por_mes = self.session.query(
            func.strftime("%Y-%m", Factura.fecha_emision),
            func.count(Factura.id),
            func.sum(Factura.total),
        ).filter(
            Factura.fecha_emision >= fecha_desde,
            Factura.fecha_emision <= fecha_hasta,
            Factura.estado == EstadoFactura.EMITIDA.value,
        ).group_by(func.strftime("%Y-%m", Factura.fecha_emision)).all()

        return {
            "total_facturado": float(total_facturado),
            "cantidad_facturas": cantidad_facturas,
            "por_tipo": [(t, int(c), float(s or 0)) for t, c, s in por_tipo],
            "por_mes": [(m, int(c), float(s or 0)) for m, c, s in por_mes],
        }

    def _recalcular_totales(self, factura: Factura) -> Factura:
        subtotal = 0.0
        iva_total = 0.0
        for det in factura.detalles:
            det.subtotal = round(det.cantidad * det.precio_unitario - det.bonificacion, 2)
            det.importe_iva = round(det.subtotal * det.alicuota_iva / 100, 2)
            subtotal += det.subtotal
            iva_total += det.importe_iva

        factura.subtotal = round(subtotal, 2)
        factura.iva_total = round(iva_total, 2)
        factura.total = round(subtotal + iva_total + factura.percepcion_iibb
                              + factura.percepcion_iva + factura.otros_impuestos
                              - factura.bonificacion, 2)
        self.session.flush()
        return factura

    def reemitir(self, factura_id: int) -> Factura:
        original = self.get_by_id(factura_id)
        if not original:
            raise DatabaseError(f"Factura original {factura_id} no encontrada")

        data = {
            "tipo_comprobante": original.tipo_comprobante,
            "punto_venta": original.punto_venta,
            "cliente_id": original.cliente_id,
            "cuit_cliente": original.cuit_cliente,
            "razon_social_cliente": original.razon_social_cliente,
            "condicion_iva_cliente": original.condicion_iva_cliente,
            "domicilio_cliente": original.domicilio_cliente,
            "concepto": original.concepto,
            "moneda": original.moneda,
            "cotizacion": original.cotizacion,
            "observaciones": f"Reemision de factura original #{original.numero_factura}",
        }

        detalles = []
        for det in original.detalles:
            detalles.append({
                "producto_id": det.producto_id,
                "codigo_producto": det.codigo_producto,
                "descripcion": det.descripcion,
                "cantidad": det.cantidad,
                "precio_unitario": det.precio_unitario,
                "alicuota_iva": det.alicuota_iva,
                "bonificacion": det.bonificacion,
            })

        return self.create(data, detalles)


class TokenRepository:
    def __init__(self, session: scoped_session):
        self.session = session

    def get_valid_token(self, service: str, cuit: str) -> Optional[TokenWSAA]:
        now = datetime.now()
        return self.session.query(TokenWSAA).filter(
            TokenWSAA.service == service,
            TokenWSAA.cuit == cuit,
            TokenWSAA.expiration_time > now,
        ).order_by(desc(TokenWSAA.expiration_time)).first()

    def save_token(self, service: str, token: str, sign: str,
                   expiration_time: datetime, cuit: str,
                   cert_hash: str, encrypted: bool = False) -> TokenWSAA:
        try:
            t = TokenWSAA(
                service=service,
                token=token,
                sign=sign,
                expiration_time=expiration_time,
                cuit=cuit,
                certificate_hash=cert_hash,
                encrypted=encrypted,
            )
            self.session.add(t)
            self.session.flush()
            return t
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error guardando token: {e}")

    def clean_expired(self):
        self.session.query(TokenWSAA).filter(
            TokenWSAA.expiration_time < datetime.now()
        ).delete()
        self.session.flush()


class AuditoriaRepository:
    def __init__(self, session: scoped_session):
        self.session = session

    def registrar(self, usuario: str, accion: str, entidad: Optional[str] = None,
                  entidad_id: Optional[int] = None, detalle: Optional[str] = None,
                  nivel: str = "INFO", session_id: Optional[str] = None):
        try:
            audit = Auditoria(
                usuario=usuario,
                accion=accion,
                entidad=entidad,
                entidad_id=entidad_id,
                detalle=detalle,
                nivel=nivel,
                session_id=session_id,
            )
            self.session.add(audit)
            self.session.flush()
        except Exception as e:
            logger.warning(f"Error registrando auditoria: {e}")

    def listar(self, limit: int = 100, offset: int = 0) -> List[Auditoria]:
        return self.session.query(Auditoria).order_by(
            desc(Auditoria.timestamp)
        ).offset(offset).limit(limit).all()


class ConfiguracionRepository:
    def __init__(self, session: scoped_session):
        self.session = session

    def get(self, clave: str, default: Optional[str] = None) -> Optional[str]:
        cfg = self.session.query(Configuracion).filter(
            Configuracion.clave == clave
        ).first()
        return cfg.valor if cfg else default

    def set(self, clave: str, valor: str, categoria: str = "general",
            descripcion: Optional[str] = None, encriptado: bool = False):
        cfg = self.session.query(Configuracion).filter(
            Configuracion.clave == clave
        ).first()
        try:
            if cfg:
                cfg.valor = valor
                cfg.categoria = categoria
                cfg.descripcion = descripcion
                cfg.encriptado = encriptado
            else:
                cfg = Configuracion(
                    clave=clave, valor=valor, categoria=categoria,
                    descripcion=descripcion, encriptado=encriptado,
                )
                self.session.add(cfg)
            self.session.flush()
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error guardando configuracion: {e}")

    def get_categoria(self, categoria: str) -> Dict[str, str]:
        configs = self.session.query(Configuracion).filter(
            Configuracion.categoria == categoria
        ).all()
        return {c.clave: c.valor for c in configs}

    def get_all(self) -> Dict[str, str]:
        configs = self.session.query(Configuracion).all()
        return {c.clave: c.valor for c in configs}
