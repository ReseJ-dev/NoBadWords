"""Application-wide Qt styles."""

APPLICATION_STYLESHEET: str = """
QMainWindow, QWidget#centralWidget {
    background-color: #f4f6f8;
    color: #17202a;
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
    border-radius: 8px;
}
QLabel[sectionTitle="true"] {
    font-size: 15px;
    font-weight: 600;
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
QPushButton#chooseVideoButton {
    background-color: #2878b5;
    border: none;
    border-radius: 5px;
    color: #ffffff;
    font-weight: 600;
    padding: 8px 14px;
}
QPushButton#chooseVideoButton:hover {
    background-color: #1f659b;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #dce1e6;
}
"""
