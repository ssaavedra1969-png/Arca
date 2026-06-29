#!/bin/bash
set -e

echo "============================================"
echo "  ARCA Facturador - Configuracion Inicial"
echo "============================================"
echo ""

echo "[1/5] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3.10+ no encontrado"
    exit 1
fi
python3 --version

echo "[2/5] Verificando OpenSSL..."
if ! command -v openssl &> /dev/null; then
    echo "WARNING: OpenSSL no encontrado"
fi

echo "[3/5] Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Entorno virtual creado"
else
    echo "Entorno virtual ya existe"
fi

echo "[4/5] Instalando dependencias..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "Dependencias instaladas"

echo "[5/5] Creando estructura de carpetas..."
mkdir -p certs data data/backups logs temp resources

echo ""
echo "============================================"
echo "  Instalacion completada!"
echo "============================================"
echo ""
echo "Para iniciar: source venv/bin/activate && python main.py"
echo "O: chmod +x run.sh && ./run.sh"
echo ""
