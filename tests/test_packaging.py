"""Windows packaging configuration tests."""

from pathlib import Path
import sys

from app.core.ffmpeg_utils import find_executable
from app.core.resources import resource_path


ROOT = Path(__file__).resolve().parents[1]


def test_packaging_files_define_windowed_executable() -> None:
    spec = (ROOT / "VideoProfanityCensor.spec").read_text(encoding="utf-8")
    build_script = (ROOT / "scripts/build_windows.py").read_text(encoding="utf-8")
    assert 'name="VideoProfanityCensor"' in spec
    assert "console=False" in spec
    assert "collect_all(\"faster_whisper\")" in spec
    assert "PyInstaller.__main__.run" in build_script


def test_resource_path_uses_pyinstaller_bundle(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_path("resources/app_icon.svg") == tmp_path / "app/resources/app_icon.svg"


def test_bundled_ffmpeg_is_preferred(monkeypatch, tmp_path: Path) -> None:
    bundled = tmp_path / "app/ffmpeg/bin/ffmpeg.exe"
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"exe")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr("app.core.ffmpeg_utils.shutil.which", lambda name: "PATH/ffmpeg")
    assert find_executable("ffmpeg") == bundled.resolve()
