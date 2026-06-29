import time
from lxml import etree


class WSAA:
    Token = ""
    Sign = ""

    def Conectar(self, url, timeout=30):
        pass

    def CreateTRA(self, service, ttl=43200):
        tra = etree.Element("loginTicketRequest")
        header = etree.SubElement(tra, "header")
        etree.SubElement(header, "uniqueId").text = str(int(time.time() * 1000))
        etree.SubElement(header, "generationTime").text = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        etree.SubElement(header, "expirationTime").text = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + ttl))
        etree.SubElement(tra, "service").text = service
        return etree.tostring(tra, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    def SignTRA(self, cms, cert_path, key_path):
        from lxml import etree as et
        signed = et.Element("loginTicketRequestFirmado")
        et.SubElement(signed, "cms").text = "CMS_FIRMADO_SIMULADO_PYAFIPWS"
        return et.tostring(signed, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    def LoginCMS(self, cms_firmado):
        self.Token = f"TOKEN_WSAA_SIMULADO_{int(time.time())}"
        self.Sign = f"SIGN_WSAA_SIMULADO_{int(time.time())}"
        return True
