"""
API REST interna para integracion con sistemas contables.
Ejecutar: uvicorn api_main:app --host 127.0.0.1 --port 8742
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

from config import ConfigManager
from core.facturador import Facturador, create_facturador
from core.models import FacturaModel, ResultadoFactura
from database.models import get_session_factory
from database.repositories import FacturaRepository, ContribuyenteRepository
from utils.exceptions import ARCAError, ValidationError

app = FastAPI(
    title="ARCA Facturador API",
    description="API REST interna para facturacion electronica ARCA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = ConfigManager.get_settings()
facturador = None


class FacturaRequest(BaseModel):
    tipo_comprobante: int
    punto_venta: int
    cuit_cliente: str
    razon_social_cliente: str
    condicion_iva_cliente: int = 5
    domicilio_cliente: Optional[str] = None
    concepto: str = "PRODUCTOS"
    moneda: str = "ARS"
    cotizacion: float = 1.0
    detalles: List[Dict[str, Any]]
    observaciones: Optional[str] = None


class FacturaResponse(BaseModel):
    success: bool
    cae: Optional[str] = None
    numero_factura: Optional[int] = None
    factura_id: Optional[int] = None
    error_message: Optional[str] = None


@app.on_event("startup")
async def startup():
    global facturador
    facturador = create_facturador(settings)


@app.get("/health", tags=["Sistema"])
async def health():
    return {
        "status": "ok",
        "app": "ARCA Facturador",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/facturas/emitir", response_model=FacturaResponse, tags=["Facturacion"])
async def emitir_factura(factura: FacturaRequest,
                          x_api_key: Optional[str] = Header(None)):
    if x_api_key and x_api_key != settings.get("api_key", ""):
        raise HTTPException(status_code=403, detail="API Key invalida")

    try:
        data = factura.model_dump()
        resultado = facturador.emitir_factura(data)
        return FacturaResponse(
            success=resultado.success,
            cae=resultado.cae,
            numero_factura=resultado.numero_factura,
            factura_id=resultado.factura_id,
            error_message=resultado.error_message,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ARCAError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")


@app.get("/facturas/{factura_id}", tags=["Facturacion"])
async def obtener_factura(factura_id: int):
    session = get_session_factory(str(settings.get_db_path()))()
    try:
        repo = FacturaRepository(session)
        factura = repo.get_by_id(factura_id)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        return {
            "id": factura.id,
            "uuid": factura.uuid,
            "tipo_comprobante": factura.tipo_comprobante,
            "punto_venta": factura.punto_venta,
            "numero": factura.numero_factura,
            "cae": factura.cae,
            "fecha": factura.fecha_emision.isoformat(),
            "cliente": factura.razon_social_cliente,
            "cuit": factura.cuit_cliente,
            "total": factura.total,
            "estado": factura.estado,
            "detalles": [
                {
                    "descripcion": d.descripcion,
                    "cantidad": d.cantidad,
                    "precio_unitario": d.precio_unitario,
                    "subtotal": d.subtotal,
                }
                for d in factura.detalles
            ],
        }
    finally:
        session.close()


@app.get("/facturas", tags=["Facturacion"])
async def listar_facturas(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    tipo: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    cliente: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
):
    filters = {}
    if desde:
        filters["fecha_desde"] = datetime.fromisoformat(desde)
    if hasta:
        filters["fecha_hasta"] = datetime.fromisoformat(hasta)
    if tipo:
        filters["tipo_comprobante"] = tipo
    if estado:
        filters["estado"] = estado.upper()
    if cliente:
        if cliente.replace("-", "").isdigit():
            filters["cuit_cliente"] = cliente
        else:
            filters["razon_social"] = cliente

    session = get_session_factory(str(settings.get_db_path()))()
    try:
        repo = FacturaRepository(session)
        resultados, total = repo.search(filters, limit=limit, offset=offset)
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "resultados": [
                {
                    "id": f.id,
                    "tipo": f.tipo_comprobante,
                    "pv": f.punto_venta,
                    "numero": f.numero_factura,
                    "cae": f.cae,
                    "fecha": f.fecha_emision.isoformat(),
                    "cliente": f.razon_social_cliente,
                    "cuit": f.cuit_cliente,
                    "total": f.total,
                    "estado": f.estado,
                }
                for f in resultados
            ],
        }
    finally:
        session.close()


@app.get("/clientes", tags=["Clientes"])
async def buscar_clientes(q: str = Query("", min_length=1)):
    session = get_session_factory(str(settings.get_db_path()))()
    try:
        repo = ContribuyenteRepository(session)
        resultados = repo.search(q)
        return [
            {
                "id": c.id,
                "cuit": c.cuit,
                "razon_social": c.razon_social,
                "condicion_iva": c.condicion_iva,
                "domicilio": c.domicilio,
            }
            for c in resultados
        ]
    finally:
        session.close()


@app.get("/estadisticas", tags=["Reportes"])
async def estadisticas(
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
):
    session = get_session_factory(str(settings.get_db_path()))()
    try:
        repo = FacturaRepository(session)
        if desde:
            f_desde = datetime.fromisoformat(desde).date()
        else:
            f_desde = None
        if hasta:
            f_hasta = datetime.fromisoformat(hasta).date()
        else:
            f_hasta = None
        stats = repo.get_estadisticas(f_desde, f_hasta)
        return stats
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8742)
