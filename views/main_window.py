import os
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStatusBar, QLabel
)
from views.viewer.side_by_side import SideBySideViewer
from views.sidebar.settings_sidebar import SettingsSidebar


class MainWindow(QMainWindow):
    """Janela principal da aplicação Engraver."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Engraver — Preparação para Gravação a Laser")
        self.resize(1360, 820)
        self.setMinimumSize(1080, 680)

        # Configura ícone da janela
        import sys
        if getattr(sys, "frozen", False) or hasattr(sys, "__compiled__"):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "resources", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Central layout
        central_widget = QWidget()
        central_layout = QHBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # 1. Left: Side-by-Side Synchronized Viewer (expands)
        self.viewer = SideBySideViewer(self)
        central_layout.addWidget(self.viewer, stretch=1)

        # 2. Right: Fixed Settings Sidebar (380px)
        self.sidebar = SettingsSidebar(self)
        central_layout.addWidget(self.sidebar, stretch=0)

        self.setCentralWidget(central_widget)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #0E0C15;
                border-top: 1px solid #2D2845;
                color: #A5A1B8;
                font-size: 11px;
                padding: 2px 10px;
            }
        """)
        self.setStatusBar(self.status_bar)

        self.lbl_status = QLabel("Pronto")
        self.lbl_status.setStyleSheet("color: #A5A1B8;")
        self.status_bar.addWidget(self.lbl_status)

        self.lbl_app_info = QLabel("Engraver v2.0 • PySide6 / C Engine")
        self.lbl_app_info.setStyleSheet("color: #5E5873;")
        self.status_bar.addPermanentWidget(self.lbl_app_info)

    def set_status(self, text: str):
        self.lbl_status.setText(text)

    def closeEvent(self, event):
        from PySide6.QtCore import QThreadPool
        pool = QThreadPool.globalInstance()
        if pool.activeThreadCount() > 0:
            pool.waitForDone(1500)
        super().closeEvent(event)
