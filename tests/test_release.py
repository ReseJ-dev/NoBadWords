"""First-release documentation and version consistency checks."""

from pathlib import Path

from app import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_consistent() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    installer = (ROOT / "installer/VideoProfanityCensor.iss").read_text(
        encoding="utf-8"
    )
    assert f'version = "{__version__}"' in pyproject
    assert f'#define MyAppVersion "{__version__}"' in installer


def test_readme_contains_release_operations_guidance() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    required_sections = (
        "Development setup", "Windows and FFmpeg setup", "CPU and NVIDIA CUDA",
        "Using the application", "Build the Windows executable",
        "Build the Windows installer", "Troubleshooting", "Known limitations",
    )
    assert all(f"## {section}" in readme for section in required_sections)
    assert "python -m app.main" in readme
    assert "python scripts/build_windows.py" in readme
    assert "python scripts/build_installer.py" in readme
