"""Tests for polished workflow labels, menus, and processing states."""

from PySide6.QtWidgets import QApplication, QLabel, QMenu

from app.gui.main_window import MainWindow


def action_texts(menu: QMenu) -> list[str]:
    return [action.text().replace("&", "") for action in menu.actions() if not action.isSeparator()]


def test_workflow_sections_are_numbered_and_clear() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    section_titles = [
        label.text()
        for label in window.findChildren(QLabel)
        if label.property("sectionTitle")
    ]

    assert "1. Select Video" in section_titles
    assert "2. Configure Scan / 3. Scan Video" in section_titles
    assert "4. Review Detections" in section_titles
    assert "5. Export Video" in section_titles
    assert "scan a video" in window.detection_count_label.text()
    window.close()
    application.processEvents()


def test_application_menus_and_shortcuts() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert action_texts(window.file_menu) == ["Open Video...", "Export Video...", "Exit"]
    assert action_texts(window.tools_menu) == ["Settings"]
    assert action_texts(window.help_menu) == ["About"]
    assert window.open_action.shortcut().toString() == "Ctrl+O"
    assert window.export_action.shortcut().toString() == "Ctrl+E"
    assert not window.export_action.isEnabled()
    window.close()
    application.processEvents()


def test_processing_state_disables_conflicting_actions_and_restores_labels() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()

    window._set_scan_controls_enabled(False)
    window.scan_settings_widget.scan_button.setText("Scanning...")

    assert not window.open_action.isEnabled()
    assert not window.review_widget.isEnabled()
    assert not window.preview_widget.isEnabled()
    assert window.scan_settings_widget.scan_button.text() == "Scanning..."

    window.scan_settings_widget.scan_button.setText("Scan Video")
    window._set_scan_controls_enabled(True)
    assert window.open_action.isEnabled()
    assert window.scan_settings_widget.scan_button.text() == "Scan Video"
    window.close()
    application.processEvents()
