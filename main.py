import datetime
import os
import sys


def get_app_dir():
    if getattr(sys, "frozen", False) or hasattr(sys, "__compiled__"):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# Garantir que stdout e stderr nunca sejam None no Windows para evitar AttributeError
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _handle_fatal_exception(exc_type, exc_value, exc_traceback):
    """Manipulador global para capturar exceções não tratadas e exibir feedback visível."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    import traceback
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    # 1. Gravar no arquivo de log
    try:
        log_dir = get_app_dir()
        log_path = os.path.join(log_dir, "engraver_crash.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH LOG [{datetime.datetime.now().isoformat()}] ---\n")
            f.write(tb_text)
    except Exception:
        pass

    # 2. Imprimir no stderr se disponível
    try:
        if sys.stderr is not None:
            sys.stderr.write(tb_text)
    except Exception:
        pass

    # 3. No Windows, exibir diálogo nativo de MessageBox para não fechar silenciosamente
    if sys.platform == "win32":
        try:
            import ctypes
            error_msg = (
                "O Engraver encontrou um erro inesperado e precisou ser encerrado:\n\n"
                f"{tb_text}\n\n"
                "O log completo foi registrado em 'engraver_crash.log'."
            )
            ctypes.windll.user32.MessageBoxW(0, error_msg, "Engraver — Erro Fatal", 0x10)
        except Exception:
            pass


sys.excepthook = _handle_fatal_exception


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

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from views.main_window import MainWindow
    from controllers.app_controller import AppController

    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Engraver")
    app.setApplicationDisplayName("Engraver — Preparação para Gravação a Laser")
    app.setDesktopFileName("engraver")

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
    app.aboutToQuit.connect(controller.cleanup)

    window.show()
    exit_code = app.exec()
    controller.cleanup()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
