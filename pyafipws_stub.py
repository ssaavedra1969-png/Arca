"""
Stub de compatibilidad para PyAfipWs.
Proporciona las mismas clases que pyafipws pero funciona con Python 3.11+.
Para desarrollo/pruebas - usa respuestas simuladas.
"""
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class WSAA:
    Token = ""
    Sign = ""

    def Conectar(self, url, timeout=30):
        pass

    def CreateTRA(self, service, ttl=43200):
        from lxml import etree
        tra = etree.Element("loginTicketRequest")
        etree.SubElement(tra, "header").text = "header"
        etree.SubElement(tra, "service").text = service
        return etree.tostring(tra, pretty_print=True)

    def SignTRA(self, cms, cert_path, key_path):
        from lxml import etree
        signed = etree.Element("signed")
        etree.SubElement(signed, "cms").text = "CMS_FIRMADO_SIMULADO"
        return etree.tostring(signed, pretty_print=True)

    def LoginCMS(self, cms_firmado):
        self.Token = f"TOKEN_WSAA_SIMULADO_{int(time.time())}"
        self.Sign = f"SIGN_WSAA_SIMULADO_{int(time.time())}"
        return True


class WSFEv1:
    Resultado = "A"
    CAE = ""
    CAEFchVto = ""
    CbteDesde = ""
    CbteHasta = ""
    Errores = ""
    Observaciones = ""
    XmlRequest = ""
    XmlResponse = ""
    _items = []
    _ivas = []
    _tributos = []

    def Conectar(self, url, timeout=30):
        pass

    def CrearFactura(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._items = []
        self._ivas = []
        self._tributos = []

    def AgregarItem(self, **kwargs):
        self._items.append(kwargs)

    def AgregarIva(self, Id_iva, Base_imp, Importe):
        self._ivas.append({"Id_iva": Id_iva, "Base_imp": Base_imp, "Importe": Importe})

    def AgregarTributo(self, **kwargs):
        self._tributos.append(kwargs)

    def CalcularServicio(self):
        pass

    def CAESolicitar(self):
        self.Resultado = "A"
        self.CAE = f"{random.randint(10**13, 10**14 - 1)}"
        vto = datetime.now() + timedelta(days=30)
        self.CAEFchVto = vto.strftime("%Y%m%d")
        self.CbteDesde = str(getattr(self, "cbt_desde", 1) or 1)
        self.CbteHasta = str(getattr(self, "cbt_hasta", 1) or 1)
        self.XmlRequest = "<xml>request_simulado</xml>"
        self.XmlResponse = f"<xml><CAE>{self.CAE}</CAE><Resultado>A</Resultado></xml>"
        return True

    def CompUltimoAutorizado(self, tipo_cbte, punto_vta):
        self.Resultado = "1"
        return True


# Stub para WSAA
class WSSrPadronA5:
    EsValido = False
    RazonSocial = ""
    IdImpuesto = 5
    DomicilioFiscal = ""

    def Conectar(self, url=""):
        pass

    def Consultar(self, cuit):
        if len(str(cuit)) == 11:
            self.EsValido = True
            self.RazonSocial = f"Contribuyente {cuit[:4]}..."
            self.IdImpuesto = 6
            self.DomicilioFiscal = "Av. Siempre Viva 123"
        return self.EsValido


class WSSrPadronA100:
    def Conectar(self, url=""):
        pass
