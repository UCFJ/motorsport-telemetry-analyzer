"""Application entry point for the telemetry analyzer UI."""

import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .styles import APPLICATION_STYLE


def main() -> int:
    """Create and run the Qt application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Motorsport Telemetry Performance Analyzer")
    app.setStyleSheet(APPLICATION_STYLE)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
