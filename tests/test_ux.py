"""Tests for polished workflow labels, menus, and processing states."""

from PySide6.QtWidgets import QApplication, QMenu

from app.gui.main_window import MainWindow
from app.core.models import ProfanityMatch, ScanResult, VideoFile, WordTimestamp


def action_texts(menu: QMenu) -> list[str]:
    return [action.text().replace("&", "") for action in menu.actions() if not action.isSeparator()]


def test_workflow_reveals_only_the_current_stage() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.scan_settings_section.isHidden()
    assert window.review_stage.isHidden()
    assert window.export_section.isHidden()
    assert window.video_metadata.isHidden()
    assert window.video_drop_area.minimumHeight() >= 190
    assert window.video_drop_area.choose_button.text() == "Choose Video"
    window.close()
    application.processEvents()


def test_advanced_scan_settings_start_collapsed() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.scan_settings_widget.advanced_panel.isHidden()
    window.scan_settings_widget.advanced_button.setChecked(True)
    assert not window.scan_settings_widget.advanced_panel.isHidden()
    window.close()
    application.processEvents()


def test_completed_scan_replaces_setup_with_review_workflow(tmp_path) -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    path = tmp_path / "video.mp4"
    path.write_bytes(b"video")
    window.state.selected_video = VideoFile.from_path(path)
    result = ScanResult(
        [WordTimestamp("word", 1.0, 1.3, 0.9)],
        [ProfanityMatch("word", "word", 1.0, 1.3, 0.9, "manual")],
    )
    window._on_transcription_succeeded(result)

    assert window.video_input_section.isHidden()
    assert window.scan_settings_section.isHidden()
    assert not window.review_stage.isHidden()
    assert not window.export_section.isHidden()
    assert window.export_controls.mode_combo.currentText() == "Beep"
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
