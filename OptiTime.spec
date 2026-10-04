# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import copy_metadata

datas = [('C:\\Users\\andy9\\OneDrive\\Bureau\\OptiTime\\app.py', '.'), ('C:\\Users\\andy9\\OneDrive\\Bureau\\OptiTime\\modules', 'modules'), ('C:\\Users\\andy9\\OneDrive\\Bureau\\OptiTime\\assets', 'assets')]
binaries = []
hiddenimports = ['win32timezone', 'win32com.client', 'pythoncom', 'plyer.platforms.win.notification']
datas += copy_metadata('streamlit')
datas += copy_metadata('streamlit_lottie')
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pandas')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('altair')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('streamlit_lottie')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\andy9\\OneDrive\\Bureau\\OptiTime\\run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'notebook', 'pytest', 'sphinx', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OptiTime',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\andy9\\OneDrive\\Bureau\\OptiTime\\assets\\icon.ico'],
    contents_directory='internal',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OptiTime',
)
