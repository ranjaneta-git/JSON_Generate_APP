"""Application entry point."""

from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication
from bmiot_configtool_v2.ui.main_window import MainWindow
from bmiot_configtool_v2.ui.styles import APP_STYLE


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BMIoT ConfigTool")
    app.setApplicationVersion("2.0")
    app.setStyleSheet(APP_STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
