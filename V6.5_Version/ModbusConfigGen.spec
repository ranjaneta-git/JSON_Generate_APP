# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['modbus_tkinter_app_v6.6_complete.py'],
    pathex=[],
    binaries=[],
    datas=[('forward_engine.py', '.'), ('reverse_engine.py', '.'), ('transform_wrapper.py', '.'), ('bmiot_constants.py', '.'), ('json_formatter.py', '.'), ('ui_helpers.py', '.')],
    hiddenimports=['forward_engine', 'reverse_engine', 'transform_wrapper', 'bmiot_constants', 'json_formatter', 'ui_helpers'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'pandas', 'matplotlib', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ModbusConfigGen',
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
)
