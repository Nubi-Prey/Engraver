from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSplitter
)
from views.viewer.canvas_view import CanvasView
from views.components.loading_spinner import LoadingSpinner


class SideBySideViewer(QWidget):
    """Contêiner com dois visores sincronizados: Original vs Simulação."""
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Toolbar superior
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel("ÁREA DE INSPEÇÃO")
        title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #A5A1B8; letter-spacing: 0.5px;")
        toolbar.addWidget(title_lbl)

        toolbar.addStretch()

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setStyleSheet("""
            background-color: #1F1C2E;
            color: #C084FC;
            font-weight: bold;
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid #2D2845;
        """)
        toolbar.addWidget(self.lbl_zoom)

        self.btn_fit = QPushButton("⛶ Ajustar")
        self.btn_fit.setToolTip("Ajustar imagem ao tamanho da tela")
        self.btn_fit.setStyleSheet(self._toolbar_btn_style())
        self.btn_fit.clicked.connect(self.fit_both)
        toolbar.addWidget(self.btn_fit)

        self.btn_1to1 = QPushButton("1:1 Pixel")
        self.btn_1to1.setToolTip("Exibir em tamanho real 100%")
        self.btn_1to1.setStyleSheet(self._toolbar_btn_style())
        self.btn_1to1.clicked.connect(self.zoom_1_to_1_both)
        toolbar.addWidget(self.btn_1to1)

        main_layout.addLayout(toolbar)

        # Divisão central Lado a Lado
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2D2845;
                width: 2px;
            }
        """)

        # Painel Esquerdo: Imagem Original
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)

        header_orig = QHBoxLayout()
        lbl_orig_title = QLabel("IMAGEM ORIGINAL")
        lbl_orig_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #F8FAFC;")
        header_orig.addWidget(lbl_orig_title)
        header_orig.addStretch()
        self.lbl_orig_dims = QLabel("-- x -- px")
        self.lbl_orig_dims.setStyleSheet("color: #5E5873; font-size: 11px;")
        header_orig.addWidget(self.lbl_orig_dims)
        left_layout.addLayout(header_orig)

        self.canvas_orig = CanvasView(placeholder_text="Nenhuma imagem carregada")
        left_layout.addWidget(self.canvas_orig)

        # Painel Direito: Simulação Dithering
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(4)

        header_sim = QHBoxLayout()
        header_sim.setSpacing(6)
        lbl_sim_title = QLabel("SIMULAÇÃO - DITHERING")
        lbl_sim_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #C084FC;")
        header_sim.addWidget(lbl_sim_title)

        self.spinner = LoadingSpinner(size=14, line_width=2.0, color="#C084FC", track_color="#1F1C2E")
        header_sim.addWidget(self.spinner)

        header_sim.addStretch()
        self.lbl_sim_status = QLabel("Aguardando processamento")
        self.lbl_sim_status.setStyleSheet("color: #5E5873; font-size: 11px;")
        header_sim.addWidget(self.lbl_sim_status)
        right_layout.addLayout(header_sim)

        self.canvas_sim = CanvasView(placeholder_text="Aguardando simulação...")
        right_layout.addWidget(self.canvas_sim)

        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setSizes([600, 600])

        main_layout.addWidget(splitter)

        # Sincronização mútua entre os dois visores
        self.canvas_orig.zoomChanged.connect(self._on_orig_zoom)
        self.canvas_sim.zoomChanged.connect(self._on_sim_zoom)
        self.canvas_orig.panChanged.connect(self._on_orig_pan)
        self.canvas_sim.panChanged.connect(self._on_sim_pan)

    def _on_orig_pan(self, h: int, v: int):
        self.canvas_sim.sync_scroll_from(self.canvas_orig)

    def _on_sim_pan(self, h: int, v: int):
        self.canvas_orig.sync_scroll_from(self.canvas_sim)

    def _toolbar_btn_style(self):
        return """
            QPushButton {
                background-color: #1F1C2E;
                border: 1px solid #6366F1;
                border-radius: 4px;
                color: #F8FAFC;
                font-size: 11px;
                padding: 4px 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: #FFFFFF;
                border-color: #C084FC;
            }
        """

    def _on_orig_zoom(self, zoom):
        self.canvas_sim.set_zoom_absolute(zoom)
        self.lbl_zoom.setText(f"{int(round(zoom * 100))}%")

    def _on_sim_zoom(self, zoom):
        self.canvas_orig.set_zoom_absolute(zoom)
        self.lbl_zoom.setText(f"{int(round(zoom * 100))}%")

    def set_loading(self, loading: bool, text: str = ""):
        """Exibe ou oculta o spinner animado e atualiza o texto de status."""
        if loading:
            self.spinner.start()
            if text:
                self.lbl_sim_status.setText(text)
        else:
            self.spinner.stop()
            if text:
                self.lbl_sim_status.setText(text)

    def set_original_image(self, qimg: QImage, dims_text: str):
        self.canvas_orig.set_image(qimg)
        self.lbl_orig_dims.setText(dims_text)
        self.fit_both()

    def set_simulated_image(self, qimg: QImage, status_text: str = "Pronto"):
        self.set_loading(False, status_text)
        self.canvas_sim.set_image(qimg)
        # Sincroniza a simulação com a escala e enquadramento atual do original
        self.canvas_sim.set_zoom_absolute(self.canvas_orig.current_zoom)
        self.canvas_sim.sync_scroll_from(self.canvas_orig)

    def fit_both(self):
        self.canvas_orig.fit_in_view()
        self.canvas_sim.fit_in_view()
        zoom = self.canvas_orig.current_zoom
        self.canvas_sim.set_zoom_absolute(zoom)
        self.lbl_zoom.setText(f"{int(round(zoom * 100))}%")

    def zoom_1_to_1_both(self):
        self.canvas_orig.zoom_1_to_1()
        self.canvas_sim.zoom_1_to_1()

    def set_zoom_both(self, zoom: float):
        self.canvas_orig.set_zoom_absolute(zoom)
        self.canvas_sim.set_zoom_absolute(zoom)
        self.lbl_zoom.setText(f"{int(round(zoom * 100))}%")
