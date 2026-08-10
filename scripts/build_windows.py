"""Build the Windows GUI executable with PyInstaller."""

from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]


def create_windows_icon(destination: Path) -> Path:
    """Render the SVG icon and wrap its PNG bytes in an ICO container."""
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    application = QGuiApplication.instance() or QGuiApplication([])
    image = QImage(256, 256, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    QSvgRenderer(str(ROOT / "src/app/resources/app_icon.svg")).render(painter)
    painter.end()
    png = QByteArray()
    buffer = QBuffer(png)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError("Could not render the Windows application icon.")
    payload = bytes(png)
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(payload), 22)
    destination.write_bytes(header + entry + payload)
    return destination


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Windows executable builds must run on Windows.")
    try:
        import PyInstaller.__main__
    except ImportError as error:
        raise SystemExit("Install build dependencies with: pip install -e .[build]") from error

    create_windows_icon(ROOT / "build/app_icon.ico")
    PyInstaller.__main__.run([
        str(ROOT / "VideoProfanityCensor.spec"), "--noconfirm", "--clean"
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
