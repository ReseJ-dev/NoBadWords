"""Static checks for the reproducible Windows installer configuration."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_inno_setup_has_install_uninstall_and_shortcuts() -> None:
    script = (ROOT / "installer/VideoProfanityCensor.iss").read_text(encoding="utf-8")
    assert "AppId={{D31D02BC-3BEC-47B9-9258-F17A524D67C6}" in script
    assert "AppVersion={#MyAppVersion}" in script
    assert 'Name: "{group}\\{#MyAppName}"' in script
    assert 'Name: "desktopicon"' in script and "Flags: unchecked" in script
    assert "UninstallDisplayIcon=" in script
    assert "SetupIconFile=" in script
    assert "uninsdelete" not in script.lower()


def test_installer_build_uses_argument_list_without_shell() -> None:
    script = (ROOT / "scripts/build_installer.py").read_text(encoding="utf-8")
    assert "subprocess.run(" in script
    assert "shell=True" not in script
    assert "INNO_SETUP_COMPILER" in script
