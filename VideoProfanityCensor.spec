# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH)
datas = [(str(ROOT / "src/app/resources"), "app/resources")]
binaries = []
ffmpeg_bin = ROOT / "vendor/ffmpeg/bin"
for executable in ("ffmpeg.exe", "ffprobe.exe"):
    candidate = ffmpeg_bin / executable
    if candidate.is_file():
        binaries.append((str(candidate), "app/ffmpeg/bin"))

whisper_datas, whisper_binaries, whisper_hiddenimports = collect_all("faster_whisper")
datas += whisper_datas
binaries += whisper_binaries

a = Analysis(
    [str(ROOT / "src/app/main.py")], pathex=[str(ROOT / "src")],
    binaries=binaries, datas=datas, hiddenimports=whisper_hiddenimports,
    hookspath=[], runtime_hooks=[], excludes=["pytest"], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="VideoProfanityCensor",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False, icon=str(ROOT / "build/app_icon.ico"),
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=True,
    name="VideoProfanityCensor",
)
