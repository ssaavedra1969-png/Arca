import random
from datetime import datetime, timedelta


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
        self.XmlRequest = "<xml version='1.0'><request><CAESolicitar/></request></xml>"
        self.XmlResponse = (
            f"<xml version='1.0'>"
            f"<CAEResponse>"
            f"<CAE>{self.CAE}</CAE>"
            f"<Resultado>A</Resultado>"
            f"<Vencimiento>{self.CAEFchVto}</Vencimiento>"
            f"</CAEResponse>"
            f"</xml>"
        )
        return True

    def CompUltimoAutorizado(self, tipo_cbte, punto_vta):
        self.Resultado = "1"
        return True
