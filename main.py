import os
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from views.main_window import MainWindow
from controllers.app_controller import AppController


def get_app_dir():
    if getattr(sys, "frozen", False) or hasattr(sys, "__compiled__"):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_stylesheet():
    qss_path = os.path.join(get_app_dir(), "resources", "styles.qss")
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"[Engraver] Warning: Failed to load styles.qss: {e}")
    return ""


def main():
    # Despacho direto para interface CLI se invocado com argumento "cli"
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        import cli
        sys.argv.pop(1)
        sys.exit(cli.run_cli())

    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Engraver")
    app.setApplicationDisplayName("Engraver — Preparação para Gravação a Laser")

    # Set application icon
    icon_path = os.path.join(get_app_dir(), "resources", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Load custom QSS theme
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # Initialize MVC
    window = MainWindow()
    controller = AppController(window)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
