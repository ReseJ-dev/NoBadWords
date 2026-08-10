"""Resource lookup that works from source and from a PyInstaller bundle."""

from pathlib import Path
import sys


def resource_path(relative_path: str | Path) -> Path:
    """Return an absolute path for an application resource."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    root = Path(bundle_root) / "app" if bundle_root else Path(__file__).resolve().parents[1]
    return root / Path(relative_path)
