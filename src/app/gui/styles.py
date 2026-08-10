"""Application-wide Qt styles."""

APPLICATION_STYLESHEET: str = """
QMainWindow, QWidget#centralWidget {
    background-color: #f7f8fa;
    color: #17212b;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QLabel#pageHeading { font-size: 27px; font-weight: 700; color: #111827; }
QLabel#pageSubtitle { color: #6b7280; font-size: 14px; }
QFrame[section="true"] {
    background-color: #ffffff;
    border: 1px solid #e5e9ef;
    border-radius: 14px;
}
QLabel[sectionTitle="true"] {
    color: #17212b;
    font-size: 17px;
    font-weight: 650;
}
QLabel[fieldCaption="true"] { color: #667085; font-size: 9pt; }
QWidget#videoDropArea {
    background-color: #fbfcfe;
    border: 2px dashed #b9c4d0;
    border-radius: 12px;
    min-height: 190px;
}
QWidget#videoDropArea[dragActive="true"] {
    background-color: #edf6ff;
    border-color: #2878b5;
}
QLabel#dropIcon { color: #2878b5; font-size: 34px; qproperty-alignment: AlignCenter; }
QLabel#dropPrompt { color: #243447; font-size: 17px; font-weight: 600; qproperty-alignment: AlignCenter; }
QLabel#dropHint { color: #8a96a3; qproperty-alignment: AlignCenter; }
QPushButton {
    background-color: #ffffff;
    border: 1px solid #d0d7df;
    border-radius: 8px;
    color: #263746;
    min-height: 34px;
    padding: 2px 14px;
}
QPushButton:hover { background-color: #f3f7fa; border-color: #91a2b2; }
QPushButton:disabled { background-color: #eef1f4; border-color: #e1e5e9; color: #9aa4ad; }
QPushButton[primary="true"] {
    background-color: #2878b5;
    border: none;
    color: #ffffff;
    font-weight: 650;
    min-width: 128px;
}
QPushButton[primary="true"]:hover { background-color: #1f659b; }
QPushButton[primary="true"]:disabled { background-color: #a9bfd0; color: #eef4f8; }
QPushButton[danger="true"] { background-color: #b23b3b; border: none; color: #ffffff; font-weight: 600; }
QPushButton#settingsButton { min-width: 38px; max-width: 38px; font-size: 18px; border: none; background: transparent; }
QToolButton#advancedSettingsButton { border: none; color: #526579; padding: 4px 0; font-weight: 600; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cfd7df;
    border-radius: 7px;
    min-height: 36px;
    min-width: 120px;
    padding: 0 10px;
}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus { border: 2px solid #2878b5; }
QSlider::groove:horizontal { height: 4px; background: #d9e0e7; border-radius: 2px; }
QSlider::handle:horizontal { width: 16px; margin: -6px 0; border-radius: 8px; background: #2878b5; }
QTableView {
    background-color: #ffffff;
    alternate-background-color: #fafbfc;
    border: none;
    gridline-color: transparent;
    selection-background-color: #e8f3fb;
    selection-color: #17212b;
}
QHeaderView::section {
    background-color: #ffffff;
    color: #7a8794;
    border: none;
    border-bottom: 1px solid #e8ebef;
    font-weight: 600;
    padding: 8px;
}
QLabel#previewSourceStatus, QLabel#detectionCount, QLabel#effectiveCensorshipDuration { color: #667085; }
QMenuBar { background-color: #f7f8fa; color: #77828e; }
QMenu { background-color: #ffffff; }
QStatusBar { background-color: #ffffff; border-top: 1px solid #e5e9ef; color: #667085; }
"""
