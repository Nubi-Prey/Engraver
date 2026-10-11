from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QRadioButton, QButtonGroup,
    QProgressBar, QFrame, QTabWidget
)
from views.components.slider_spinbox import SliderSpinBox
from views.components.aspect_ratio_lock import AspectRatioLock


def create_card_frame():
    card = QFrame()
    card.setStyleSheet("""
        QFrame {
            background-color: #171523;
            border: 1px solid #2D2845;
            border-radius: 6px;
        }
    """)
    return card


class SettingsSidebar(QWidget):
    """Barra lateral com abas temáticas e rodapé fixo de exportação (Zero Scroll)."""
    settingsChanged = Signal()
    openFileClicked = Signal()
    exportClicked = Signal()
    presetSelected = Signal(str)
    presetSaveClicked = Signal()
    presetDeleteClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(380)
        self.setStyleSheet("""
            SettingsSidebar {
                background-color: #0E0C15;
                border-left: 1px solid #2D2845;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 1. Abas Superiores
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2D2845;
                background-color: #171523;
                border-radius: 6px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #1F1C2E;
                color: #A5A1B8;
                padding: 7px 18px;
                border: 1px solid #2D2845;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                letter-spacing: 0.5px;
            }
            QTabBar::tab:selected {
                background-color: #171523;
                color: #C084FC;
                border-color: #2D2845;
                border-bottom: 2px solid #A855F7;
            }
            QTabBar::tab:hover:!selected {
                background-color: #242036;
                color: #F8FAFC;
            }
        """)

        # --- Aba 1: Imagem & Ajustes ---
        tab_image_container = QWidget()
        layout_image = QVBoxLayout(tab_image_container)
        layout_image.setContentsMargins(8, 8, 8, 8)
        layout_image.setSpacing(8)
        self._build_source_card(layout_image)
        self._build_preprocessing_card(layout_image)
        layout_image.addStretch()

        scroll_image = self._create_tab_scroll(tab_image_container)

        # --- Aba 2: Laser & Dither ---
        tab_laser_container = QWidget()
        layout_laser = QVBoxLayout(tab_laser_container)
        layout_laser.setContentsMargins(8, 8, 8, 8)
        layout_laser.setSpacing(8)
        self._build_presets_card(layout_laser)
        self._build_dimensions_card(layout_laser)
        self._build_dithering_card(layout_laser)
        layout_laser.addStretch()

        scroll_laser = self._create_tab_scroll(tab_laser_container)

        self.tabs.addTab(scroll_image, "🎨 Imagem")
        self.tabs.addTab(scroll_laser, "⚡ Gravação")
        main_layout.addWidget(self.tabs, stretch=1)

        # 2. Rodapé Fixo de Ação (Resumo de Saída + Exportar)
        footer_frame = QWidget()
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(6)

        self._build_resolution_card(footer_layout)
        self._build_export_card(footer_layout)

        main_layout.addWidget(footer_frame, stretch=0)

    def _create_tab_scroll(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #0E0C15;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #1F1C2E;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2D2845;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        scroll.setWidget(widget)
        return scroll

    def _create_card_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #A5A1B8; letter-spacing: 0.5px;")
        return lbl

    def _build_presets_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(8)

        l.addWidget(self._create_card_title("PREDEFINIÇÕES (PRESETS)"))

        row = QHBoxLayout()
        row.setSpacing(6)

        self.combo_presets = QComboBox()
        self.combo_presets.setStyleSheet("""
            QComboBox {
                background-color: #1F1C2E;
                border: 1px solid #2D2845;
                border-radius: 4px;
                padding: 4px 8px;
                color: #F8FAFC;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1F1C2E;
                color: #F8FAFC;
                selection-background-color: #A855F7;
                border: 1px solid #2D2845;
            }
        """)
        self.combo_presets.currentTextChanged.connect(self._on_preset_changed)
        row.addWidget(self.combo_presets, stretch=1)

        self.btn_save_preset = QPushButton("Salvar")
        self.btn_save_preset.setToolTip("Salvar ajustes atuais como novo preset")
        self.btn_save_preset.setStyleSheet("""
            QPushButton {
                background-color: #1F1C2E;
                border: 1px solid #6366F1;
                border-radius: 4px;
                padding: 4px 10px;
                color: #C084FC;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: #FFFFFF;
                border-color: #C084FC;
            }
        """)
        self.btn_save_preset.clicked.connect(self.presetSaveClicked)
        row.addWidget(self.btn_save_preset)

        self.btn_delete_preset = QPushButton("Excluir")
        self.btn_delete_preset.setToolTip("Excluir preset selecionado")
        self.btn_delete_preset.setStyleSheet("""
            QPushButton {
                background-color: #1F1C2E;
                border: 1px solid #2D2845;
                border-radius: 4px;
                padding: 4px 8px;
                color: #F87171;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: #FFFFFF;
            }
        """)
        self.btn_delete_preset.clicked.connect(self.presetDeleteClicked)
        row.addWidget(self.btn_delete_preset)

        l.addLayout(row)
        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _build_source_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(6)

        l.addWidget(self._create_card_title("ORIGEM DA IMAGEM"))

        row = QHBoxLayout()
        self.entry_file = QLineEdit()
        self.entry_file.setReadOnly(True)
        self.entry_file.setPlaceholderText("Nenhum arquivo selecionado")
        self.entry_file.setStyleSheet("""
            QLineEdit {
                background-color: #1F1C2E;
                border: 1px solid #2D2845;
                border-radius: 4px;
                padding: 4px 8px;
                color: #F8FAFC;
                font-size: 12px;
            }
        """)
        row.addWidget(self.entry_file)

        self.btn_open = QPushButton("📁 Abrir")
        self.btn_open.setStyleSheet("""
            QPushButton {
                background-color: #1F1C2E;
                border: 1px solid #6366F1;
                border-radius: 4px;
                padding: 5px 12px;
                color: #F8FAFC;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #6366F1;
                border-color: #C084FC;
            }
        """)
        self.btn_open.clicked.connect(self.openFileClicked)
        row.addWidget(self.btn_open)
        l.addLayout(row)

        self.lbl_info_mp = QLabel("Original: -- MP")
        self.lbl_info_mp.setStyleSheet("color: #A5A1B8; font-size: 11px;")
        l.addWidget(self.lbl_info_mp)

        self.lbl_info_dims = QLabel("Dimensões: -- mm x -- mm @ -- DPI")
        self.lbl_info_dims.setStyleSheet("color: #5E5873; font-size: 11px;")
        l.addWidget(self.lbl_info_dims)

        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _emit_settings_changed(self, *args):
        self.settingsChanged.emit()

    def _on_bg_button_toggled(self, button, checked):
        if checked:
            self.settingsChanged.emit()

    def _build_dimensions_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(8)

        l.addWidget(self._create_card_title("CONTROLES FÍSICOS"))

        self.aspect_lock = AspectRatioLock()
        self.aspect_lock.dimensionsChanged.connect(self._emit_settings_changed)
        l.addWidget(self.aspect_lock)

        self.slider_dpi = SliderSpinBox("DPI ALVO", min_val=96, max_val=1000, default_val=300, step=10, suffix="DPI")
        self.slider_dpi.valueChanged.connect(self._emit_settings_changed)
        l.addWidget(self.slider_dpi)

        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _build_resolution_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 8, 12, 8)
        l.setSpacing(4)

        l.addWidget(self._create_card_title("RESUMO DE SAÍDA"))

        self.lbl_res_out1 = QLabel("Saída: -- px | -- Pixels")
        self.lbl_res_out1.setStyleSheet("color: #F8FAFC; font-size: 12px; font-weight: 500;")
        l.addWidget(self.lbl_res_out1)

        self.lbl_res_alert = QLabel("Aguardando imagem")
        self.lbl_res_alert.setStyleSheet("""
            background-color: #1F1C2E;
            color: #A5A1B8;
            font-size: 11px;
            font-weight: bold;
            padding: 3px 6px;
            border-radius: 4px;
            border: 1px solid #2D2845;
        """)
        l.addWidget(self.lbl_res_alert)

        self.lbl_res_out2 = QLabel("Saída: -- px @ -- DPI")
        self.lbl_res_out2.setStyleSheet("color: #5E5873; font-size: 11px;")
        l.addWidget(self.lbl_res_out2)

        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _build_preprocessing_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(6)

        l.addWidget(self._create_card_title("PRÉ-PROCESSAMENTO"))

        self.slider_bright = SliderSpinBox("BRILHO", 0, 100, 50)
        self.slider_bright.valueChanged.connect(self._emit_settings_changed)
        l.addWidget(self.slider_bright)

        self.slider_contrast = SliderSpinBox("CONTRASTE", 0, 100, 50)
        self.slider_contrast.valueChanged.connect(self._emit_settings_changed)
        l.addWidget(self.slider_contrast)

        # Gamma row
        gamma_row = QHBoxLayout()
        lbl_g = QLabel("CORREÇÃO GAMA (1.2)")
        lbl_g.setStyleSheet("font-weight: 600; font-size: 12px; color: #A5A1B8;")
        gamma_row.addWidget(lbl_g)
        gamma_row.addStretch()
        self.chk_gamma = QCheckBox("Ativo")
        self.chk_gamma.setChecked(True)
        self.chk_gamma.setStyleSheet("""
            QCheckBox {
                color: #A5A1B8;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #2D2845;
                background-color: #1F1C2E;
            }
            QCheckBox::indicator:checked {
                background-color: #A855F7;
                border-color: #C084FC;
            }
        """)
        self.chk_gamma.toggled.connect(self._emit_settings_changed)
        gamma_row.addWidget(self.chk_gamma)
        l.addLayout(gamma_row)

        self.slider_sharpen = SliderSpinBox("NITIDEZ (Unsharp)", 0, 100, 85)
        self.slider_sharpen.valueChanged.connect(self._emit_settings_changed)
        l.addWidget(self.slider_sharpen)

        # Background composition row
        bg_row = QHBoxLayout()
        lbl_bg = QLabel("FUNDO (Alpha):")
        lbl_bg.setStyleSheet("font-weight: 600; font-size: 12px; color: #A5A1B8;")
        bg_row.addWidget(lbl_bg)
        bg_row.addStretch()

        self.bg_group = QButtonGroup(self)
        self.rb_bg_black = QRadioButton("Preto")
        self.rb_bg_white = QRadioButton("Branco")
        self.rb_bg_black.setChecked(True)

        for rb in [self.rb_bg_black, self.rb_bg_white]:
            rb.setStyleSheet("""
                QRadioButton {
                    color: #A5A1B8;
                    font-size: 12px;
                }
                QRadioButton::indicator {
                    width: 14px;
                    height: 14px;
                    border-radius: 7px;
                    border: 1px solid #2D2845;
                    background-color: #1F1C2E;
                }
                QRadioButton::indicator:checked {
                    background-color: #A855F7;
                    border-color: #C084FC;
                }
            """)
            self.bg_group.addButton(rb)
            bg_row.addWidget(rb)

        self.bg_group.buttonToggled.connect(self._on_bg_button_toggled)
        l.addLayout(bg_row)

        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _build_dithering_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(6)

        l.addWidget(self._create_card_title("MOTOR DE DITHERING"))

        # Method
        method_row = QHBoxLayout()
        lbl_m = QLabel("MÉTODO:")
        lbl_m.setStyleSheet("font-weight: 600; font-size: 12px; color: #A5A1B8;")
        method_row.addWidget(lbl_m)

        self.combo_method = QComboBox()
        self.combo_method.addItems(["Atkinson", "Floyd-Steinberg", "Jarvis-Judice-Ninke"])
        self.combo_method.setStyleSheet("""
            QComboBox {
                background-color: #1F1C2E;
                border: 1px solid #2D2845;
                border-radius: 4px;
                padding: 4px 8px;
                color: #F8FAFC;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #1F1C2E;
                color: #F8FAFC;
                selection-background-color: #A855F7;
                border: 1px solid #2D2845;
            }
        """)
        self.combo_method.currentTextChanged.connect(self._emit_settings_changed)
        method_row.addWidget(self.combo_method, stretch=1)
        l.addLayout(method_row)

        # Invert colors row
        inv_row = QHBoxLayout()
        lbl_inv = QLabel("INVERTER CORES:")
        lbl_inv.setStyleSheet("font-weight: 600; font-size: 12px; color: #A5A1B8;")
        inv_row.addWidget(lbl_inv)
        inv_row.addStretch()

        self.chk_invert = QCheckBox("Negativo")
        self.chk_invert.setStyleSheet("""
            QCheckBox { color: #A5A1B8; font-size: 12px; }
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border-radius: 4px;
                border: 1px solid #2D2845;
                background-color: #1F1C2E;
            }
            QCheckBox::indicator:checked {
                background-color: #A855F7;
                border-color: #C084FC;
            }
        """)
        self.chk_invert.toggled.connect(self._emit_settings_changed)
        inv_row.addWidget(self.chk_invert)
        l.addLayout(inv_row)

        self.slider_density = SliderSpinBox("DENSIDADE", 1, 10, 1)
        self.slider_density.valueChanged.connect(self._emit_settings_changed)
        l.addWidget(self.slider_density)

        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _build_export_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(6)

        self.btn_export = QPushButton("EXPORTAR IMAGEM")
        self.btn_export.setFixedHeight(44)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #A855F7, stop:1 #6366F1);
                border: none;
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #C084FC, stop:1 #818CF8);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333EA, stop:1 #4F46E5);
            }
            QPushButton:disabled {
                background: #1F1C2E;
                color: #5E5873;
                border: 1px solid #2D2845;
            }
        """)
        self.btn_export.clicked.connect(self.exportClicked)
        l.addWidget(self.btn_export)

        self.progress_export = QProgressBar()
        self.progress_export.setFixedHeight(5)
        self.progress_export.setTextVisible(False)
        self.progress_export.setRange(0, 0)  # Indeterminate
        self.progress_export.setVisible(False)
        self.progress_export.setStyleSheet("""
            QProgressBar {
                background-color: #1F1C2E;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #A855F7;
                border-radius: 2px;
            }
        """)
        l.addWidget(self.progress_export)

        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _on_preset_changed(self, text):
        if text:
            self.presetSelected.emit(text)

    def update_presets_list(self, presets_list, current="Padrão"):
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        self.combo_presets.addItems(presets_list)
        if current in presets_list:
            self.combo_presets.setCurrentText(current)
        self.combo_presets.blockSignals(False)

    def get_all_settings(self):
        w, h = self.aspect_lock.get_dimensions()
        return {
            "width_mm": w,
            "height_mm": h,
            "target_dpi": int(self.slider_dpi.value()),
            "brightness": int(self.slider_bright.value()),
            "contrast": int(self.slider_contrast.value()),
            "gamma_active": self.chk_gamma.isChecked(),
            "sharpen": int(self.slider_sharpen.value()),
            "background": "Preto" if self.rb_bg_black.isChecked() else "Branco",
            "dither_method": self.combo_method.currentText(),
            "invert_colors": self.chk_invert.isChecked(),
            "density": int(self.slider_density.value())
        }

    def apply_preset_settings(self, s: dict):
        self.blockSignals(True)
        if "target_dpi" in s:
            self.slider_dpi.setValue(s["target_dpi"])
        if "brightness" in s:
            self.slider_bright.setValue(s["brightness"])
        if "contrast" in s:
            self.slider_contrast.setValue(s["contrast"])
        if "gamma_active" in s:
            self.chk_gamma.setChecked(s["gamma_active"])
        if "sharpen" in s:
            self.slider_sharpen.setValue(s["sharpen"])
        if "background" in s:
            if s["background"] == "Preto":
                self.rb_bg_black.setChecked(True)
            else:
                self.rb_bg_white.setChecked(True)
        if "dither_method" in s:
            idx = self.combo_method.findText(s["dither_method"])
            if idx >= 0:
                self.combo_method.setCurrentIndex(idx)
        if "invert_colors" in s:
            self.chk_invert.setChecked(s["invert_colors"])
        if "density" in s:
            self.slider_density.setValue(s["density"])
        self.blockSignals(False)
        self.settingsChanged.emit()

    def set_file_info(self, filename: str, original_mp: str, width_mm: float, height_mm: float, dpi: int):
        self.entry_file.setText(filename)
        self.lbl_info_mp.setText(f"Original: {original_mp} MP")
        self.lbl_info_dims.setText(f"Dimensões: {width_mm:.1f}mm x {height_mm:.1f}mm @ {dpi} DPI")

    def set_resolution_alerts(self, out1_text: str, alert_text: str, alert_color: str, out2_text: str):
        self.lbl_res_out1.setText(out1_text)
        self.lbl_res_alert.setText(alert_text)
        self.lbl_res_alert.setStyleSheet(f"""
            background-color: #1F1C2E;
            color: {alert_color};
            font-size: 11px;
            font-weight: bold;
            padding: 3px 6px;
            border-radius: 4px;
            border: 1px solid #2D2845;
        """)
        self.lbl_res_out2.setText(out2_text)

    def set_exporting_state(self, exporting: bool):
        self.btn_export.setEnabled(not exporting)
        self.btn_export.setText("Exportando..." if exporting else "EXPORTAR IMAGEM")
        self.progress_export.setVisible(exporting)
