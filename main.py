#!/usr/bin/env python3
"""Punto de entrada principal para ARCA Facturador."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ui.main import main

if __name__ == "__main__":
    main()
