"""Tests for the desktop application foundation."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFrame

from app.gui.main_window import MainWindow


def test_main_window_foundation() -> None:
    application = QApplication.instance() or QApplication([])
    window = MainWindow()

    assert window.windowTitle() == "Video Profanity Censor"
    assert window.minimumWidth() >= 900
    assert window.minimumHeight() >= 600
    assert window.statusBar().currentMessage() == "Ready"

    section_names = {
        section.objectName()
        for section in window.findChildren(QFrame)
        if section.objectName()
    }
    assert {
        "videoInput",
        "scanSettings",
        "detectedProfanity",
        "exportControls",
    } <= section_names

    window.close()
    application.processEvents()

