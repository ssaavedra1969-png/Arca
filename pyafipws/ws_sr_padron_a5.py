class WSSrPadronA5:
    EsValido = False
    RazonSocial = ""
    IdImpuesto = 5
    DomicilioFiscal = ""
    CategoriaMonotributo = ""

    def Conectar(self, url=""):
        pass

    def Consultar(self, cuit):
        cuit_str = str(cuit).replace("-", "")
        if len(cuit_str) == 11:
            self.EsValido = True
            self.RazonSocial = f"Contribuyente {cuit_str[:4]}...{cuit_str[-4:]}"
            self.IdImpuesto = 6
            self.DomicilioFiscal = "Av. Siempre Viva 123, CABA"
            self.CategoriaMonotributo = "A"
        return self.EsValido
