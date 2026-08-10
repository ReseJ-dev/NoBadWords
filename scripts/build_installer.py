"""Build the Windows installer with the Inno Setup compiler."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def find_inno_compiler() -> Path | None:
    """Find ISCC through configuration, PATH, or standard Windows locations."""
    configured = os.environ.get("INNO_SETUP_COMPILER")
    candidates = [Path(configured)] if configured else []
    on_path = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if on_path:
        candidates.append(Path(on_path))
    for variable in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(variable)
        if base:
            candidates.append(Path(base) / "Inno Setup 6" / "ISCC.exe")
    return next((path.resolve() for path in candidates if path.is_file()), None)


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Windows installer builds must run on Windows.")
    executable = ROOT / "dist/VideoProfanityCensor/VideoProfanityCensor.exe"
    if not executable.is_file():
        raise SystemExit("Build the executable first: python scripts/build_windows.py")
    compiler = find_inno_compiler()
    if compiler is None:
        raise SystemExit(
            "Inno Setup 6 was not found. Install it or set INNO_SETUP_COMPILER."
        )
    result = subprocess.run(
        [str(compiler), str(ROOT / "installer/VideoProfanityCensor.iss")],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
