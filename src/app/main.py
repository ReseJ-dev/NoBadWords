"""PySide6 application entry point."""

import logging
import sys
from collections.abc import Sequence

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.core.config import configure_logging
from app.core.resources import resource_path
from app.gui.main_window import MainWindow
from app.gui.styles import APPLICATION_STYLESHEET

LOGGER = logging.getLogger(__name__)


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    """Create and configure the Qt application."""
    application = QApplication(list(argv) if argv is not None else sys.argv)
    application.setOrganizationName("VideoProfanityCensor")
    application.setApplicationName("Video Profanity Censor")
    application.setWindowIcon(QIcon(str(resource_path("resources/app_icon.svg"))))
    application.setStyleSheet(APPLICATION_STYLESHEET)
    return application


def main(argv: Sequence[str] | None = None) -> int:
    """Start the desktop application and return its exit code."""
    configure_logging()
    LOGGER.info("Starting Video Profanity Censor")
    application = create_application(argv)
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
