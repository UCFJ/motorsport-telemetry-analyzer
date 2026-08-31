"""Application entry point for the telemetry analyzer UI."""

import ctypes
import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def main(argv=None) -> int:
    """Run the internal logger mode or create the Qt application."""
    application_args = list(sys.argv[1:] if argv is None else argv)

    if application_args and application_args[0] == "--logger":
        from src.ingestion.shared_memory_logger import main as logger_main

        return logger_main(application_args[1:]) or 0

    from PySide6.QtWidgets import QApplication

    from .main_window import MainWindow
    from .styles import APPLICATION_STYLE

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "MotorsportTelemetryAnalyzer"
        )

    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS"))
    else:
        base_path = Path(__file__).resolve().parent.parent.parent
    icon_path = base_path / "assets" / "telemetry_analtzer.png"

    app = QApplication([sys.argv[0], *application_args])
    app.setApplicationName("Motorsport Telemetry Performance Analyzer")
    icon = QIcon(str(icon_path))
    if not icon.isNull():
        app.setWindowIcon(icon)
    app.setStyleSheet(APPLICATION_STYLE)

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
