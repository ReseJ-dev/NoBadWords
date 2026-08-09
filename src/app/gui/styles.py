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
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #dce1e6;
}
"""

