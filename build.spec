# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('templates', 'templates'),
        ('config.yaml', '.'),
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'PyAfipWs',
        'PyAfipWs.wsaa',
        'PyAfipWs.wsfev1',
        'PyAfipWs.ws_sr_padron_a5',
        'cryptography',
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.primitives.ciphers.aead',
        'lxml',
        'lxml._elementpath',
        'lxml.etree',
        'openpyxl',
        'openpyxl.cell._writer',
        'openpyxl.reader.excel',
        'reportlab',
        'reportlab.graphics.barcode',
        'reportlab.graphics.barcode.qr',
        'reportlab.lib',
        'reportlab.platypus',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'qrcode',
        'plyer',
        'pydantic',
        'pydantic_settings',
        'loguru',
        'httpx',
        'babel',
        'babel.numbers',
        'babel.dates',
        'bcrypt',
        'dotenv',
        'apscheduler',
        'schedule',
        'sqlalchemy',
        'sqlalchemy.sql.default_comparator',
        'yaml',
        'database',
        'database.models',
        'database.repositories',
        'core',
        'core.auth',
        'core.facturador',
        'core.validador',
        'core.models',
        'ui',
        'ui.main',
        'ui.panel_configuracion',
        'ui.panel_facturacion',
        'ui.panel_historial',
        'ui.panel_reportes',
        'reports',
        'reports.pdf_generator',
        'reports.excel_generator',
        'reports.xml_generator',
        'utils',
        'utils.logger',
        'utils.validators',
        'utils.formatters',
        'utils.encryption',
        'utils.exceptions',
        'utils.firebase_sync',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest',
        'pytest',
        'test',
        'distutils',
        'setuptools',
        'pip',
        'email',
        'http.server',
        'socketserver',
        'xmlrpc',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ARCA_Facturador',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico',
)

# Windows installer
if sys.platform == 'win32':
    from PyInstaller.utils.win32 import versioninfo

    # Create version info
    ver = versioninfo.VSVersionInfo(
        ffi=versioninfo.FixedFileInfo(
            filevers=(1, 0, 0, 0),
            prodvers=(1, 0, 0, 0),
        ),
        kids=[
            versioninfo.StringFileInfo(
                [
                    versioninfo.StringTable(
                        '040904B0',
                        [
                            versioninfo.StringStruct('CompanyName', 'ARCA Facturador'),
                            versioninfo.StringStruct('FileDescription', 'ARCA Facturador - Facturacion Electronica'),
                            versioninfo.StringStruct('FileVersion', '1.0.0'),
                            versioninfo.StringStruct('InternalName', 'ARCA_Facturador'),
                            versioninfo.StringStruct('LegalCopyright', '© 2026'),
                            versioninfo.StringStruct('OriginalFilename', 'ARCA_Facturador.exe'),
                            versioninfo.StringStruct('ProductName', 'ARCA Facturador'),
                            versioninfo.StringStruct('ProductVersion', '1.0.0'),
                        ],
                    )
                ]
            ),
        ],
    )

    exe.prefix = ''
    exe.description = 'Sistema de Facturacion Electronica ARCA'
    exe.version = ver
    exe.company_name = 'ARCA Facturador'
    exe.product_name = 'ARCA Facturador'
    exe.internal_name = 'ARCA_Facturador'
    exe.original_filename = 'ARCA_Facturador.exe'
