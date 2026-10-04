import PyInstaller.__main__
import os
import shutil
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parent
SCRIPT_TO_COMPILE = "main.py"
NAME = "OptiTime"

build_dir = WORK_DIR / "build"
dist_dir = WORK_DIR / "dist"
if build_dir.exists(): shutil.rmtree(build_dir)
if dist_dir.exists(): shutil.rmtree(dist_dir)

args = [
    str(WORK_DIR / SCRIPT_TO_COMPILE),
    f'--name={NAME}',
    '--onedir',
    '--clean',
    '--noconsole',
    f'--add-data={WORK_DIR / "modules"}{os.pathsep}modules',
    f'--add-data={WORK_DIR / "assets"}{os.pathsep}assets',
    '--collect-all=flet',
    '--collect-all=pandas',
    '--exclude-module=matplotlib',
    '--exclude-module=scipy',
    '--exclude-module=notebook',
    '--exclude-module=pytest',
    '--exclude-module=streamlit',
]

icon_path = WORK_DIR / "assets" / "icon.ico"
if icon_path.exists():
    args.append(f'--icon={icon_path}')

PyInstaller.__main__.run(args)
print(f"\n✅ Compilation réussie dans : dist/{NAME}/{NAME}.exe")