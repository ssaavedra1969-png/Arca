import time
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from loguru import logger

from config import ConfigManager
from core.auth import Authenticator, CertificateManager
from core.validador import ValidadorARCA
from core.models import FacturaModel, ResultadoFactura, DetalleFacturaModel
from database.models import (
    get_session_factory, Factura, DetalleFactura,
    Contribuyente, EstadoFactura, TipoComprobante
)
from database.repositories import (
    FacturaRepository, ContribuyenteRepository,
    TokenRepository, AuditoriaRepository
)
from utils.exceptions import (
    ARCAError, AuthError, ConnectionError, BusinessError,
    ValidationError, DatabaseError, CAEError, OfflineQueueError
)
from utils.firebase_sync import firebase_sync


class Facturador:
    def __init__(self, settings=None, authenticator: Optional[Authenticator] = None):
        self.settings = settings or ConfigManager.get_settings()
        self.authenticator = authenticator or Authenticator(self.settings)
        self.validador = ValidadorARCA(self.settings)
        self.session_factory = None
        self._initialized = False
        self._offline_queue: List[Dict[str, Any]] = []
        self._ultimo_numero_cache: Dict[str, int] = {}

    def initialize(self, session_factory=None, enc_manager=None):
        if not self.authenticator._initialized:
            self.authenticator.initialize(session_factory, enc_manager)
        self.session_factory = session_factory or get_session_factory(
            str(self.settings.get_db_path())
        )
        self._initialized = True
        logger.info("Facturador inicializado correctamente")

    def emitir_factura(self, factura_data: Dict[str, Any]) -> ResultadoFactura:
        if not self._initialized:
            raise ValidationError("Facturador no inicializado. Llame initialize() primero")

        try:
            factura_model = FacturaModel(**factura_data)
        except Exception as e:
            raise ValidationError(f"Datos de factura invalidos: {e}")

        if not factura_model.fecha_emision:
            factura_model.fecha_emision = datetime.now().date()

        valido, errores = self.validador.validar_factura(factura_model.to_dict())
        if not valido:
            raise ValidationError(f"Errores de validacion: {'; '.join(errores)}")

        if self.settings.arca_homo:
            return self._emitir_homo(factura_model)
        else:
            return self._emitir_con_reintento(factura_model)

    def _emitir_con_reintento(self, factura_model: FacturaModel, intento: int = 0) -> ResultadoFactura:
        max_intentos = self.settings.arca_retry_max_attempts
        try:
            return self._emitir_ws(factura_model)
        except (ConnectionError, TimeoutError) as e:
            if intento < max_intentos - 1:
                delay = min(
                    self.settings.arca_retry_base_delay * (2 ** intento),
                    self.settings.arca_retry_max_delay
                )
                logger.warning(f"Reintento {intento + 1}/{max_intentos} en {delay}s: {e}")
                time.sleep(delay)
                return self._emitir_con_reintento(factura_model, intento + 1)
            return self._guardar_pendiente(factura_model, str(e))
        except AuthError as e:
            logger.error(f"Error de autenticacion: {e}")
            return ResultadoFactura(
                success=False, error_message=str(e), error_code="AUTH_ERROR"
            )
        except BusinessError as e:
            return ResultadoFactura(
                success=False, error_message=str(e), error_code="BUSINESS_ERROR"
            )
        except Exception as e:
            logger.error(f"Error inesperado: {e}\n{traceback.format_exc()}")
            return self._guardar_pendiente(factura_model, str(e))

    def _emitir_ws(self, factura_model: FacturaModel) -> ResultadoFactura:
        from pyafipws.wsfev1 import WSFEv1

        try:
            token, sign = self.authenticator.authenticate("wsfe")

            wsfe = WSFEv1()
            wsfe.Conectar(
                self.settings.get_wsfe_url(),
                self.settings.arca_timeout_connect,
            )
            wsfe.CrearFactura(
                concepto=1 if factura_model.concepto in ("PRODUCTOS", "PRODUCTOS Y SERVICIOS") else 2,
                tipo_doc=80,
                nro_doc=int(factura_model.cuit_cliente),
                tipo_cbte=factura_model.tipo_comprobante,
                punto_vta=factura_model.punto_venta,
                cbt_desde=None,
                cbt_hasta=None,
                imp_total=factura_model.calcular_totales()["total"],
                imp_tot_conc=0,
                imp_neto=factura_model.calcular_totales()["subtotal"],
                imp_iva=factura_model.calcular_totales()["iva_total"],
                imp_trib=factura_model.percepcion_iibb + factura_model.percepcion_iva,
                moneda_id=factura_model.moneda,
                moneda_cotiz=factura_model.cotizacion,
                fecha_cbte=factura_model.fecha_emision.strftime("%Y%m%d"),
            )

            for det in factura_model.detalles:
                iva_id = self._get_iva_id(det.alicuota_iva)
                wsfe.AgregarItem(
                    U_Mtx=1,
                    Codigo=det.codigo_producto or "",
                    Desc=det.descripcion,
                    Cantidad=det.cantidad,
                    Precio=det.precio_unitario,
                    Importe=det.subtotal,
                    Bonif=det.bonificacion,
                    Imp_iva=det.importe_iva,
                    Id_iva=iva_id,
                )

            wsfe.AgregarIva(
                Id_iva=self._get_iva_id(factura_model.detalles[0].alicuota_iva),
                Base_imp=factura_model.calcular_totales()["subtotal"],
                Importe=factura_model.calcular_totales()["iva_total"],
            )

            cuit_emisor = self.authenticator.get_cuit()
            wsfe.CalcularServicio()
            wsfe.CAESolicitar()

            if wsfe.Resultado == "A":
                session = self.session_factory()
                try:
                    factura_repo = FacturaRepository(session)
                    cliente_repo = ContribuyenteRepository(session)

                    cliente = cliente_repo.get_by_cuit(factura_model.cuit_cliente)
                    if not cliente:
                        cliente = cliente_repo.create({
                            "cuit": factura_model.cuit_cliente,
                            "razon_social": factura_model.razon_social_cliente,
                            "condicion_iva": factura_model.condicion_iva_cliente,
                            "domicilio": factura_model.domicilio_cliente,
                        })
                        session.flush()

                    totales = factura_model.calcular_totales()
                    factura_data = {
                        "tipo_comprobante": factura_model.tipo_comprobante,
                        "punto_venta": factura_model.punto_venta,
                        "numero_factura": wsfe.CAE,
                        "cae": str(wsfe.CAE),
                        "cae_vencimiento": self._parse_fecha(wsfe.CAEFchVto),
                        "resultado": wsfe.Resultado,
                        "fecha_emision": factura_model.fecha_emision,
                        "cliente_id": cliente.id,
                        "cuit_cliente": factura_model.cuit_cliente,
                        "razon_social_cliente": factura_model.razon_social_cliente,
                        "condicion_iva_cliente": factura_model.condicion_iva_cliente,
                        "domicilio_cliente": factura_model.domicilio_cliente,
                        "concepto": factura_model.concepto,
                        "moneda": factura_model.moneda,
                        "cotizacion": factura_model.cotizacion,
                        "subtotal": totales["subtotal"],
                        "iva_total": totales["iva_total"],
                        "percepcion_iibb": factura_model.percepcion_iibb,
                        "percepcion_iva": factura_model.percepcion_iva,
                        "otros_impuestos": factura_model.otros_impuestos,
                        "bonificacion": factura_model.bonificacion,
                        "total": totales["total"],
                        "observaciones": factura_model.observaciones,
                        "estado": EstadoFactura.EMITIDA.value,
                        "factura_origen_id": factura_model.factura_origen_id,
                        "cae_original": factura_model.cae_original,
                    }

                    detalles_data = []
                    for det in factura_model.detalles:
                        detalles_data.append({
                            "codigo_producto": det.codigo_producto,
                            "descripcion": det.descripcion,
                            "cantidad": det.cantidad,
                            "precio_unitario": det.precio_unitario,
                            "alicuota_iva": det.alicuota_iva,
                            "importe_iva": det.importe_iva,
                            "bonificacion": det.bonificacion,
                            "subtotal": det.subtotal,
                        })

                    factura = factura_repo.create(factura_data, detalles_data)
                    session.commit()

                    auditoria = AuditoriaRepository(session)
                    auditoria.registrar(
                        usuario="operador",
                        accion="EMITIR_FACTURA",
                        entidad="Factura",
                        entidad_id=factura.id,
                        detalle=f"Factura tipo {factura_model.tipo_comprobante} #{factura.numero_factura} - CAE: {wsfe.CAE}",
                    )
                    session.commit()

                    numero_factura = self._parse_int(wsfe.CbteDesde) or factura.id

                    try:
                        firebase_sync.sync_factura(factura_data)
                    except Exception:
                        pass

                    logger.info(f"Factura emitida: PV={factura_model.punto_venta} "
                                f"Tipo={factura_model.tipo_comprobante} "
                                f"Nro={numero_factura} CAE={wsfe.CAE}")

                    return ResultadoFactura(
                        success=True,
                        cae=str(wsfe.CAE),
                        cae_vencimiento=self._parse_fecha(wsfe.CAEFchVto),
                        numero_factura=numero_factura,
                        resultado=wsfe.Resultado,
                        factura_id=factura.id,
                        uuid=factura.uuid,
                    )
                except Exception as e:
                    session.rollback()
                    raise DatabaseError(f"Error guardando factura: {e}")
                finally:
                    session.close()
            else:
                obs = wsfe.Observaciones or ""
                return ResultadoFactura(
                    success=False,
                    resultado=wsfe.Resultado,
                    error_message=f"ARCA rechazo la factura: {obs}",
                    error_code=wsfe.Errores,
                    xml_request=getattr(wsfe, "XmlRequest", ""),
                    xml_response=getattr(wsfe, "XmlResponse", ""),
                    observaciones=obs,
                )

        except Exception as e:
            logger.error(f"Error en _emitir_ws: {e}")
            raise

    def _emitir_homo(self, factura_model: FacturaModel) -> ResultadoFactura:
        logger.info("MODO HOMOLOGACION: simulando emision")
        import uuid
        from datetime import timedelta

        totales = factura_model.calcular_totales()
        cae_simulado = f"{int(time.time()) % 10**14:014d}"

        session = self.session_factory()
        try:
            factura_repo = FacturaRepository(session)
            cliente_repo = ContribuyenteRepository(session)

            cliente = cliente_repo.get_by_cuit(factura_model.cuit_cliente)
            if not cliente:
                cliente = cliente_repo.create({
                    "cuit": factura_model.cuit_cliente,
                    "razon_social": factura_model.razon_social_cliente,
                    "condicion_iva": factura_model.condicion_iva_cliente,
                    "domicilio": factura_model.domicilio_cliente,
                })
                session.flush()

            factura_data = {**factura_model.to_dict(), **totales}
            factura_data["cae"] = cae_simulado
            factura_data["cae_vencimiento"] = datetime.now() + timedelta(days=30)
            factura_data["resultado"] = "A"
            factura_data["estado"] = EstadoFactura.EMITIDA.value
            factura_data["numero_factura"] = 1
            factura_data["cliente_id"] = cliente.id

            detalles_data = [d.model_dump() for d in factura_model.detalles]
            factura = factura_repo.create(factura_data, detalles_data)
            session.commit()

            return ResultadoFactura(
                success=True,
                cae=cae_simulado,
                cae_vencimiento=datetime.now() + timedelta(days=30),
                numero_factura=1,
                resultado="A",
                factura_id=factura.id,
                uuid=factura.uuid,
                observaciones="MODO HOMOLOGACION - CAE SIMULADO",
            )
        except Exception as e:
            session.rollback()
            raise DatabaseError(f"Error en modo homologicion: {e}")
        finally:
            session.close()

    def _guardar_pendiente(self, factura_model: FacturaModel, error_msg: str) -> ResultadoFactura:
        logger.warning(f"Guardando factura como pendiente: {error_msg}")

        session = self.session_factory()
        try:
            factura_repo = FacturaRepository(session)
            cliente_repo = ContribuyenteRepository(session)

            cliente = cliente_repo.get_by_cuit(factura_model.cuit_cliente)
            if not cliente:
                cliente = cliente_repo.create({
                    "cuit": factura_model.cuit_cliente,
                    "razon_social": factura_model.razon_social_cliente,
                    "condicion_iva": factura_model.condicion_iva_cliente,
                    "domicilio": factura_model.domicilio_cliente,
                })
                session.flush()

            totales = factura_model.calcular_totales()
            factura_data = {
                "tipo_comprobante": factura_model.tipo_comprobante,
                "punto_venta": factura_model.punto_venta,
                "fecha_emision": factura_model.fecha_emision or datetime.now().date(),
                "cliente_id": cliente.id,
                "cuit_cliente": factura_model.cuit_cliente,
                "razon_social_cliente": factura_model.razon_social_cliente,
                "condicion_iva_cliente": factura_model.condicion_iva_cliente,
                "concepto": factura_model.concepto,
                "moneda": factura_model.moneda,
                "cotizacion": factura_model.cotizacion,
                **totales,
                "percepcion_iibb": factura_model.percepcion_iibb,
                "percepcion_iva": factura_model.percepcion_iva,
                "otros_impuestos": factura_model.otros_impuestos,
                "bonificacion": factura_model.bonificacion,
                "observaciones": factura_model.observaciones,
                "estado": EstadoFactura.PENDIENTE.value,
                "error_message": error_msg,
                "factura_origen_id": factura_model.factura_origen_id,
                "cae_original": factura_model.cae_original,
            }

            detalles_data = [
                {
                    "codigo_producto": d.codigo_producto,
                    "descripcion": d.descripcion,
                    "cantidad": d.cantidad,
                    "precio_unitario": d.precio_unitario,
                    "alicuota_iva": d.alicuota_iva,
                    "importe_iva": d.importe_iva,
                    "bonificacion": d.bonificacion,
                    "subtotal": d.subtotal,
                }
                for d in factura_model.detalles
            ]

            factura = factura_repo.create(factura_data, detalles_data)
            session.commit()

            return ResultadoFactura(
                success=False,
                factura_id=factura.id,
                uuid=factura.uuid,
                error_message=f"Factura guardada como pendiente: {error_msg}",
                error_code="PENDIENTE",
            )
        except Exception as e:
            session.rollback()
            raise DatabaseError(f"Error guardando factura pendiente: {e}")
        finally:
            session.close()

    def sincronizar_pendientes(self) -> Tuple[int, int, List[str]]:
        session = self.session_factory()
        try:
            factura_repo = FacturaRepository(session)
            pendientes = factura_repo.get_pendientes()
            exitos = 0
            fallos = 0
            errores = []

            for factura in pendientes:
                try:
                    detalles_model = [
                        DetalleFacturaModel(
                            codigo_producto=d.codigo_producto,
                            descripcion=d.descripcion,
                            cantidad=d.cantidad,
                            precio_unitario=d.precio_unitario,
                            alicuota_iva=d.alicuota_iva,
                            bonificacion=d.bonificacion,
                        )
                        for d in factura.detalles
                    ]

                    factura_model = FacturaModel(
                        tipo_comprobante=factura.tipo_comprobante,
                        punto_venta=factura.punto_venta,
                        cuit_cliente=factura.cuit_cliente,
                        razon_social_cliente=factura.razon_social_cliente,
                        condicion_iva_cliente=factura.condicion_iva_cliente,
                        detalles=[d.model_dump() for d in detalles_model],
                        concepto=factura.concepto,
                        moneda=factura.moneda,
                        cotizacion=factura.cotizacion,
                    )

                    resultado = self._emitir_ws(factura_model)
                    if resultado.success:
                        factura_repo.update_estado(
                            factura.id,
                            EstadoFactura.EMITIDA.value,
                            cae=resultado.cae,
                            numero_factura=resultado.numero_factura,
                            resultado="A",
                        )
                        session.commit()
                        exitos += 1
                    else:
                        factura.intentos += 1
                        factura.error_message = resultado.error_message
                        session.flush()
                        fallos += 1
                        errores.append(f"Factura #{factura.id}: {resultado.error_message}")

                except Exception as e:
                    fallos += 1
                    errores.append(f"Factura #{factura.id}: {e}")
                    logger.error(f"Error sincronizando factura {factura.id}: {e}")

            logger.info(f"Sincronizacion completada: {exitos} exitos, {fallos} fallos")
            return exitos, fallos, errores

        finally:
            session.close()

    def consultar_ultimo_numero(self, punto_venta: int, tipo_comprobante: int) -> int:
        cache_key = f"{punto_venta}:{tipo_comprobante}"
        if cache_key in self._ultimo_numero_cache:
            return self._ultimo_numero_cache[cache_key]

        token, sign = self.authenticator.authenticate("wsfe")
        from pyafipws.wsfev1 import WSFEv1

        wsfe = WSFEv1()
        wsfe.Conectar(self.settings.get_wsfe_url(), self.settings.arca_timeout_connect)
        wsfe.CompUltimoAutorizado(tipo_comprobante, punto_venta)

        ultimo = int(wsfe.Resultado) if wsfe.Resultado else 0
        self._ultimo_numero_cache[cache_key] = ultimo
        return ultimo

    def consultar_comprobante(self, cae: str) -> Optional[Dict[str, Any]]:
        session = self.session_factory()
        try:
            factura_repo = FacturaRepository(session)
            factura = factura_repo.get_by_cae(cae)
            if factura:
                return {
                    "id": factura.id,
                    "uuid": factura.uuid,
                    "cae": factura.cae,
                    "tipo_comprobante": factura.tipo_comprobante,
                    "punto_venta": factura.punto_venta,
                    "numero": factura.numero_factura,
                    "fecha": factura.fecha_emision,
                    "cliente": factura.razon_social_cliente,
                    "cuit": factura.cuit_cliente,
                    "total": factura.total,
                    "estado": factura.estado,
                    "detalles": [
                        {
                            "descripcion": d.descripcion,
                            "cantidad": d.cantidad,
                            "precio": d.precio_unitario,
                            "subtotal": d.subtotal,
                        }
                        for d in factura.detalles
                    ],
                }
            return None
        finally:
            session.close()

    def anular_comprobante(self, factura_id: int, motivo: str) -> Tuple[bool, str]:
        session = self.session_factory()
        try:
            factura_repo = FacturaRepository(session)
            factura = factura_repo.get_by_id(factura_id)

            if not factura:
                return False, "Factura no encontrada"

            if factura.estado == EstadoFactura.ANULADA.value:
                return False, "La factura ya fue anulada"

            factura_repo.update_estado(
                factura_id,
                EstadoFactura.ANULADA.value,
                motivo_anulacion=motivo,
            )
            session.commit()

            auditoria = AuditoriaRepository(session)
            auditoria.registrar(
                usuario="operador",
                accion="ANULAR_FACTURA",
                entidad="Factura",
                entidad_id=factura_id,
                detalle=f"Anulada factura #{factura.numero_factura}: {motivo}",
            )
            session.commit()

            logger.info(f"Factura #{factura.numero_factura} anulada: {motivo}")
            return True, "Factura anulada correctamente"

        except Exception as e:
            session.rollback()
            return False, f"Error anulando factura: {e}"
        finally:
            session.close()

    def _get_iva_id(self, alicuota: float) -> int:
        MAPA = {0.0: 3, 10.5: 4, 21.0: 5, 27.0: 6, 5.0: 8, 2.5: 9}
        return MAPA.get(alicuota, 5)

    @staticmethod
    def _parse_fecha(fecha_str: str) -> Optional[datetime]:
        if not fecha_str:
            return None
        try:
            for fmt in ("%Y%m%d", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(str(fecha_str)[:10], fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    @staticmethod
    def _parse_int(valor) -> Optional[int]:
        if not valor:
            return None
        try:
            return int(valor)
        except (ValueError, TypeError):
            return None


class FacturadorOffline:
    def __init__(self, facturador: Facturador):
        self.facturador = facturador
        self.cola: List[Dict[str, Any]] = []

    def agregar_a_cola(self, factura_data: Dict[str, Any]) -> str:
        from uuid import uuid4
        uid = str(uuid4())
        self.cola.append({
            "uuid": uid,
            "data": factura_data,
            "creado": datetime.now(),
            "intentos": 0,
        })
        logger.info(f"Factura {uid} agregada a cola offline")
        return uid

    def procesar_cola(self) -> Tuple[int, int]:
        exitos = 0
        fallos = 0
        pendientes = [f for f in self.cola if f["intentos"] < 3]

        for item in pendientes:
            try:
                resultado = self.facturador.emitir_factura(item["data"])
                if resultado.success:
                    self.cola.remove(item)
                    exitos += 1
                else:
                    item["intentos"] += 1
                    fallos += 1
            except Exception:
                item["intentos"] += 1
                fallos += 1

        return exitos, fallos

    def cola_pendiente_count(self) -> int:
        return len([f for f in self.cola if f["intentos"] < 3])


def create_facturador(settings=None) -> Facturador:
    from config import ConfigManager
    settings = settings or ConfigManager.get_settings()
    facturador = Facturador(settings)
    session_factory = get_session_factory(str(settings.get_db_path()))
    facturador.initialize(session_factory)
    return facturador
