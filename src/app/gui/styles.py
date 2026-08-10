"""Application-wide Qt styles."""

APPLICATION_STYLESHEET: str = """
QMainWindow, QWidget#centralWidget {
    background-color: #f4f6f8;
    color: #17202a;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QLabel#pageHeading {
    font-size: 24px;
    font-weight: 700;
}
QLabel#pageSubtitle {
    color: #5d6d7e;
    font-size: 13px;
}
QFrame[section="true"] {
    background-color: #ffffff;
    border: 1px solid #dce1e6;
    border-radius: 10px;
}
QLabel[sectionTitle="true"] {
    color: #1f3a52;
    font-size: 16px;
    font-weight: 700;
}
QLabel[placeholder="true"] {
    color: #85929e;
}
QWidget#videoDropArea {
    background-color: #f8fafc;
    border: 2px dashed #aab7c4;
    border-radius: 7px;
    min-height: 60px;
}
QWidget#videoDropArea[dragActive="true"] {
    background-color: #e8f4fd;
    border-color: #2878b5;
}
QLabel#dropPrompt {
    color: #5d6d7e;
    qproperty-alignment: AlignCenter;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #b8c4ce;
    border-radius: 6px;
    color: #263746;
    padding: 7px 12px;
}
QPushButton:hover {
    background-color: #edf3f7;
    border-color: #7f95a8;
}
QPushButton:disabled {
    background-color: #e9edf0;
    border-color: #d4dbe0;
    color: #97a3ad;
}
QPushButton[primary="true"] {
    background-color: #2878b5;
    border: none;
    color: #ffffff;
    font-weight: 600;
    padding: 9px 16px;
}
QPushButton[primary="true"]:hover {
    background-color: #1f659b;
}
QPushButton[primary="true"]:disabled {
    background-color: #9ab8ce;
    color: #eef4f8;
}
QPushButton[danger="true"] {
    background-color: #b23b3b;
    border: none;
    color: #ffffff;
    font-weight: 600;
}
QPushButton[danger="true"]:hover {
    background-color: #922f2f;
}
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #b8c4ce;
    border-radius: 5px;
    min-height: 24px;
    padding: 3px 6px;
}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
    border-color: #2878b5;
}
QTableView {
    alternate-background-color: #f5f8fa;
    background-color: #ffffff;
    border: 1px solid #d5dde3;
    gridline-color: #e5eaee;
    selection-background-color: #d9ecfa;
    selection-color: #17202a;
}
QHeaderView::section {
    background-color: #eaf0f4;
    border: none;
    border-bottom: 1px solid #c8d2da;
    font-weight: 600;
    padding: 6px;
}
QLabel#previewSourceStatus, QLabel#detectionCount, QLabel#effectiveCensorshipDuration {
    color: #5d6d7e;
}
QMenuBar, QMenu {
    background-color: #ffffff;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #dce1e6;
}
"""
