from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QRadioButton,
    QButtonGroup,
    QProgressBar,
    QFrame,
    QTabWidget,
)
from core.pipeline import normalize_transforms_config
from views.components.slider_spinbox import SliderSpinBox
from views.components.aspect_ratio_lock import AspectRatioLock
from views.components.transform_card import TransformCard


COMBO_STYLE = """
    QComboBox {
        background-color: #1F1C2E;
        border: 1px solid #2D2845;
        border-radius: 4px;
        padding: 4px 8px;
        color: #F8FAFC;
        font-size: 12px;
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
"""

CHECKBOX_STYLE = """
    QCheckBox {
        color: #A5A1B8;
        font-size: 11px;
        font-weight: 600;
    }
    QCheckBox::indicator {
        width: 15px;
        height: 15px;
        border-radius: 4px;
        border: 1px solid #2D2845;
        background-color: #1F1C2E;
    }
    QCheckBox::indicator:checked {
        background-color: #A855F7;
        border-color: #C084FC;
    }
"""


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
    """Barra lateral modular com Presets fixos no topo, 2 abas e rodapé fixo de exportação."""

    settingsChanged = Signal()
    openFileClicked = Signal()
    exportClicked = Signal()
    presetSelected = Signal(str)
    presetSaveClicked = Signal()
    presetDeleteClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._suppress_signals = False
        self.transform_cards = {}

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(390)
        self.setStyleSheet("""
            SettingsSidebar {
                background-color: #0E0C15;
                border-left: 1px solid #2D2845;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 0. Topo Fixo: Predefinições (Presets) — sempre visível em qualquer aba
        self._build_presets_card(main_layout)

        # 1. Abas Centrais
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

        # --- Aba 1: Imagem & Transformações Modulares ---
        tab_image_container = QWidget()
        tab_image_container.setStyleSheet("background-color: #171523;")
        layout_image = QVBoxLayout(tab_image_container)
        layout_image.setContentsMargins(8, 8, 8, 8)
        layout_image.setSpacing(6)
        self._build_source_card(layout_image)
        self._build_transforms_stack(layout_image)
        layout_image.addStretch()

        scroll_image = self._create_tab_scroll(tab_image_container)

        # --- Aba 2: Laser & Dithering ---
        tab_laser_container = QWidget()
        tab_laser_container.setStyleSheet("background-color: #171523;")
        layout_laser = QVBoxLayout(tab_laser_container)
        layout_laser.setContentsMargins(8, 8, 8, 8)
        layout_laser.setSpacing(8)
        self._build_dimensions_card(layout_laser)
        self._build_dithering_card(layout_laser)
        layout_laser.addStretch()

        scroll_laser = self._create_tab_scroll(tab_laser_container)

        self.tabs.addTab(scroll_image, "🎨 Imagem")
        self.tabs.addTab(scroll_laser, "⚡ Gravação")
        main_layout.addWidget(self.tabs, stretch=1)

        # 2. Rodapé Fixo de Ação (Resumo de Saída + Exportar)
        footer_frame = QWidget()
        footer_frame.setStyleSheet("background-color: #0E0C15;")
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
        scroll.viewport().setStyleSheet("background-color: #171523;")
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #171523;
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

    def _emit_settings_changed(self, *args):
        if not self._suppress_signals:
            self.settingsChanged.emit()

    def _on_bg_button_toggled(self, button, checked):
        if checked and not self._suppress_signals:
            self.settingsChanged.emit()

    def _build_presets_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(6)

        l.addWidget(self._create_card_title("PREDEFINIÇÕES (PRESETS)"))

        row = QHBoxLayout()
        row.setSpacing(6)

        self.combo_presets = QComboBox()
        self.combo_presets.setStyleSheet(COMBO_STYLE)
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
        l.setContentsMargins(10, 8, 10, 8)
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

        # Fundo (Alpha) — Padrão sempre Branco
        bg_row = QHBoxLayout()
        lbl_bg = QLabel("FUNDO (Alpha):")
        lbl_bg.setStyleSheet("font-weight: 600; font-size: 11px; color: #A5A1B8;")
        bg_row.addWidget(lbl_bg)
        bg_row.addStretch()

        self.bg_group = QButtonGroup(self)
        self.rb_bg_white = QRadioButton("Branco")
        self.rb_bg_black = QRadioButton("Preto")
        self.rb_bg_white.setChecked(True)

        for rb in [self.rb_bg_white, self.rb_bg_black]:
            rb.setStyleSheet("""
                QRadioButton {
                    color: #A5A1B8;
                    font-size: 11px;
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

    def _register_card(self, card: TransformCard, parent_layout):
        card.changed.connect(self._emit_settings_changed)
        self.transform_cards[card.transform_id] = card
        parent_layout.addWidget(card)
        return card

    def _build_transforms_stack(self, parent_layout):
        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(2, 4, 2, 0)
        hdr_row.addWidget(self._create_card_title("TRANSFORMAÇÕES MODULARES"))
        hdr_row.addStretch()
        hint = QLabel("Ative e ajuste cada etapa")
        hint.setStyleSheet("color: #6B6488; font-size: 10px;")
        hdr_row.addWidget(hint)
        parent_layout.addLayout(hdr_row)

        # 1. Brilho & Contraste
        c_bc = TransformCard("brightness_contrast", "1. Brilho & Contraste", default_enabled=False)
        self.slider_bright = SliderSpinBox("BRILHO", 0, 100, 50)
        self.slider_contrast = SliderSpinBox("CONTRASTE", 0, 100, 50)
        self.slider_bright.valueChanged.connect(c_bc.notify_param_changed)
        self.slider_contrast.valueChanged.connect(c_bc.notify_param_changed)
        c_bc.body_layout.addWidget(self.slider_bright)
        c_bc.body_layout.addWidget(self.slider_contrast)
        c_bc.set_summary_fn(lambda: f"B:{int(self.slider_bright.value())} C:{int(self.slider_contrast.value())}")
        c_bc.set_expanded(False)
        self._register_card(c_bc, parent_layout)

        # 2. Mixagem de Canais (Pele)
        c_cm = TransformCard("channel_mixing", "2. Mixagem de Canais", default_enabled=False)
        self.slider_mix_r = SliderSpinBox("PESO R (Pele)", 0.0, 1.0, 0.6, step=0.05, decimals=2)
        self.slider_mix_g = SliderSpinBox("PESO G", 0.0, 1.0, 0.3, step=0.05, decimals=2)
        self.slider_mix_b = SliderSpinBox("PESO B", 0.0, 1.0, 0.1, step=0.05, decimals=2)
        for s in (self.slider_mix_r, self.slider_mix_g, self.slider_mix_b):
            s.valueChanged.connect(c_cm.notify_param_changed)
            c_cm.body_layout.addWidget(s)
        c_cm.set_summary_fn(
            lambda: f"{int(round(self.slider_mix_r.value()*100))}/{int(round(self.slider_mix_g.value()*100))}/{int(round(self.slider_mix_b.value()*100))}"
        )
        c_cm.set_expanded(False)
        self._register_card(c_cm, parent_layout)

        # 3. CLAHE (Contraste Local)
        c_clahe = TransformCard("clahe", "3. CLAHE (Contraste Local)", default_enabled=False)
        self.slider_clahe_clip = SliderSpinBox("LIMITE (Clip)", 0.5, 6.0, 2.0, step=0.1, decimals=1)
        self.slider_clahe_tile = SliderSpinBox("GRADE (Tile)", 4, 16, 8, step=2)
        self.slider_clahe_clip.valueChanged.connect(c_clahe.notify_param_changed)
        self.slider_clahe_tile.valueChanged.connect(c_clahe.notify_param_changed)
        c_clahe.body_layout.addWidget(self.slider_clahe_clip)
        c_clahe.body_layout.addWidget(self.slider_clahe_tile)
        c_clahe.set_summary_fn(
            lambda: f"Clip {self.slider_clahe_clip.value():.1f} • {int(self.slider_clahe_tile.value())}×{int(self.slider_clahe_tile.value())}"
        )
        c_clahe.set_expanded(False)
        self._register_card(c_clahe, parent_layout)

        # 4. Correção Gama
        c_gamma = TransformCard("gamma", "4. Correção Gama", default_enabled=False)
        self.slider_gamma = SliderSpinBox("GAMA", 0.4, 2.5, 1.2, step=0.1, decimals=1)
        self.slider_gamma.valueChanged.connect(c_gamma.notify_param_changed)
        c_gamma.body_layout.addWidget(self.slider_gamma)
        c_gamma.set_summary_fn(lambda: f"γ {self.slider_gamma.value():.1f}")
        c_gamma.set_expanded(False)
        self._register_card(c_gamma, parent_layout)

        # 5. Densidade
        c_dens = TransformCard("density", "5. Densidade", default_enabled=False)
        self.slider_density = SliderSpinBox("NÍVEL", 1, 10, 1)
        self.slider_density.valueChanged.connect(c_dens.notify_param_changed)
        c_dens.body_layout.addWidget(self.slider_density)
        c_dens.set_summary_fn(lambda: f"Nível {int(self.slider_density.value())}")
        c_dens.set_expanded(False)
        self._register_card(c_dens, parent_layout)

        # 6. Nitidez (Unsharp / HP)
        c_sharp = TransformCard("sharpen", "6. Nitidez (Unsharp / HP)", default_enabled=False)
        self.slider_sharpen = SliderSpinBox("FORÇA (Unsharp)", 0, 100, 85)
        self.slider_sharpen.valueChanged.connect(c_sharp.notify_param_changed)
        c_sharp.body_layout.addWidget(self.slider_sharpen)

        self.chk_sharpen_hp = QCheckBox("Incluir filtro High Pass")
        self.chk_sharpen_hp.setChecked(True)
        self.chk_sharpen_hp.setStyleSheet(CHECKBOX_STYLE)
        self.chk_sharpen_hp.toggled.connect(c_sharp.notify_param_changed)
        c_sharp.body_layout.addWidget(self.chk_sharpen_hp)
        c_sharp.set_summary_fn(
            lambda: f"{int(self.slider_sharpen.value())}%{' + HP' if self.chk_sharpen_hp.isChecked() else ''}"
        )
        c_sharp.set_expanded(False)
        self._register_card(c_sharp, parent_layout)

        # 7. Suavização Bilateral
        c_bilat = TransformCard("bilateral", "7. Suavização Bilateral", default_enabled=False)
        self.slider_bilateral_passes = SliderSpinBox("PASSAGENS", 1, 6, 3)
        self.slider_bilateral_sigma = SliderSpinBox("FORÇA (Sigma)", 15, 100, 45, step=5)
        self.slider_bilateral_passes.valueChanged.connect(c_bilat.notify_param_changed)
        self.slider_bilateral_sigma.valueChanged.connect(c_bilat.notify_param_changed)
        c_bilat.body_layout.addWidget(self.slider_bilateral_passes)
        c_bilat.body_layout.addWidget(self.slider_bilateral_sigma)
        c_bilat.set_summary_fn(
            lambda: f"{int(self.slider_bilateral_passes.value())}× • σ{int(self.slider_bilateral_sigma.value())}"
        )
        c_bilat.set_expanded(False)
        self._register_card(c_bilat, parent_layout)

        # 8. Trava de Extremos
        c_clamp = TransformCard("tone_clamp", "8. Trava de Extremos", default_enabled=False)
        self.slider_white_clamp = SliderSpinBox("TRAVA BRANCO", 180, 255, 240)
        self.slider_black_clamp = SliderSpinBox("TRAVA PRETO", 0, 80, 20)
        self.slider_white_clamp.valueChanged.connect(c_clamp.notify_param_changed)
        self.slider_black_clamp.valueChanged.connect(c_clamp.notify_param_changed)
        c_clamp.body_layout.addWidget(self.slider_white_clamp)
        c_clamp.body_layout.addWidget(self.slider_black_clamp)
        c_clamp.set_summary_fn(
            lambda: f"P≤{int(self.slider_black_clamp.value())} • B≥{int(self.slider_white_clamp.value())}"
        )
        c_clamp.set_expanded(False)
        self._register_card(c_clamp, parent_layout)

        # 9. Quantização Suave
        c_quant = TransformCard("quantize", "9. Quantização Suave", default_enabled=False)

        q_lvl_row = QHBoxLayout()
        lbl_ql = QLabel("NÍVEIS:")
        lbl_ql.setStyleSheet("font-weight: 600; font-size: 11px; color: #A5A1B8;")
        q_lvl_row.addWidget(lbl_ql)
        self.combo_quantize_levels = QComboBox()
        self.combo_quantize_levels.setStyleSheet(COMBO_STYLE)
        for val, text in [
            (2, "2 (Stencil P&B)"),
            (3, "3 tons"),
            (4, "4 tons"),
            (5, "5 tons"),
            (6, "6 tons"),
            (8, "8 tons"),
        ]:
            self.combo_quantize_levels.addItem(text, val)
        self.combo_quantize_levels.setCurrentIndex(2)  # 4 tons
        self.combo_quantize_levels.currentIndexChanged.connect(c_quant.notify_param_changed)
        q_lvl_row.addWidget(self.combo_quantize_levels, stretch=1)
        c_quant.body_layout.addLayout(q_lvl_row)

        self.slider_quantize_softness = SliderSpinBox("SUAVIZAÇÃO ENTRE NÍVEIS", 0, 100, 35, step=5, suffix="%")
        self.slider_quantize_softness.valueChanged.connect(c_quant.notify_param_changed)
        c_quant.body_layout.addWidget(self.slider_quantize_softness)

        q_mode_row = QHBoxLayout()
        lbl_qm = QLabel("MODO:")
        lbl_qm.setStyleSheet("font-weight: 600; font-size: 11px; color: #A5A1B8;")
        q_mode_row.addWidget(lbl_qm)
        self.combo_quantize_mode = QComboBox()
        self.combo_quantize_mode.setStyleSheet(COMBO_STYLE)
        self.combo_quantize_mode.addItem("K-Means (Adaptativo)", "kmeans")
        self.combo_quantize_mode.addItem("Uniforme (Espaçado)", "uniform")
        self.combo_quantize_mode.currentIndexChanged.connect(c_quant.notify_param_changed)
        q_mode_row.addWidget(self.combo_quantize_mode, stretch=1)
        c_quant.body_layout.addLayout(q_mode_row)

        c_quant.set_summary_fn(
            lambda: f"{self.combo_quantize_levels.currentData()}t • Suave {int(self.slider_quantize_softness.value())}%"
        )
        c_quant.set_expanded(False)
        self._register_card(c_quant, parent_layout)

        # 10. Limpeza (Ilhas / Ruído) — Morfologia + Filtro Mediano
        c_clean = TransformCard("cleanup", "10. Limpeza (Ilhas / Ruído)", default_enabled=False)

        cl_m_row = QHBoxLayout()
        lbl_cm = QLabel("MÉTODO:")
        lbl_cm.setStyleSheet("font-weight: 600; font-size: 11px; color: #A5A1B8;")
        cl_m_row.addWidget(lbl_cm)
        self.combo_cleanup_method = QComboBox()
        self.combo_cleanup_method.setStyleSheet(COMBO_STYLE)
        self.combo_cleanup_method.addItem("Morfologia (Close + Open)", "morph_close_open")
        self.combo_cleanup_method.addItem("Filtro Mediano (Median)", "median")
        self.combo_cleanup_method.currentIndexChanged.connect(c_clean.notify_param_changed)
        cl_m_row.addWidget(self.combo_cleanup_method, stretch=1)
        c_clean.body_layout.addLayout(cl_m_row)

        cl_k_row = QHBoxLayout()
        lbl_ck = QLabel("KERNEL:")
        lbl_ck.setStyleSheet("font-weight: 600; font-size: 11px; color: #A5A1B8;")
        cl_k_row.addWidget(lbl_ck)
        self.combo_cleanup_kernel = QComboBox()
        self.combo_cleanup_kernel.setStyleSheet(COMBO_STYLE)
        self.combo_cleanup_kernel.addItem("3×3 px", 3)
        self.combo_cleanup_kernel.addItem("5×5 px", 5)
        self.combo_cleanup_kernel.currentIndexChanged.connect(c_clean.notify_param_changed)
        cl_k_row.addWidget(self.combo_cleanup_kernel, stretch=1)
        c_clean.body_layout.addLayout(cl_k_row)

        c_clean.set_summary_fn(
            lambda: f"{'Mediano' if self.combo_cleanup_method.currentData() == 'median' else 'Morf.'} {self.combo_cleanup_kernel.currentData()}×{self.combo_cleanup_kernel.currentData()}"
        )
        c_clean.set_expanded(False)
        self._register_card(c_clean, parent_layout)

    def _build_dimensions_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(8)

        l.addWidget(self._create_card_title("CONTROLES FÍSICOS"))

        self.chk_keep_native_res = QCheckBox("Manter resolução original (sem redimensionar)")
        self.chk_keep_native_res.setChecked(False)
        self.chk_keep_native_res.setStyleSheet(CHECKBOX_STYLE)
        self.chk_keep_native_res.toggled.connect(self._on_keep_native_toggled)
        l.addWidget(self.chk_keep_native_res)

        self.aspect_lock = AspectRatioLock()
        self.aspect_lock.dimensionsChanged.connect(self._emit_settings_changed)
        l.addWidget(self.aspect_lock)

        self.slider_dpi = SliderSpinBox("DPI ALVO", min_val=96, max_val=1000, default_val=300, step=10, suffix="DPI")
        self.slider_dpi.valueChanged.connect(self._emit_settings_changed)
        l.addWidget(self.slider_dpi)

        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _on_keep_native_toggled(self, checked: bool):
        self.aspect_lock.setEnabled(not checked)
        self.slider_dpi.setEnabled(not checked)
        self._emit_settings_changed()

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

    def _build_dithering_card(self, parent_layout=None):
        card = create_card_frame()
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(6)

        l.addWidget(self._create_card_title("MOTOR DE DITHERING"))

        method_row = QHBoxLayout()
        lbl_m = QLabel("MÉTODO:")
        lbl_m.setStyleSheet("font-weight: 600; font-size: 12px; color: #A5A1B8;")
        method_row.addWidget(lbl_m)

        self.combo_method = QComboBox()
        self.combo_method.addItems([
            "Atkinson",
            "Floyd-Steinberg",
            "Jarvis-Judice-Ninke",
            "Halftone (Clusters)",
        ])
        self.combo_method.setStyleSheet(COMBO_STYLE)
        self.combo_method.currentTextChanged.connect(self._on_dither_method_changed)
        method_row.addWidget(self.combo_method, stretch=1)
        l.addLayout(method_row)

        self.slider_halftone_cell = SliderSpinBox("CÉLULA HALFTONE", 3, 12, 6, suffix="px")
        self.slider_halftone_cell.valueChanged.connect(self._emit_settings_changed)
        self.slider_halftone_cell.setVisible(False)
        l.addWidget(self.slider_halftone_cell)

        inv_row = QHBoxLayout()
        lbl_inv = QLabel("INVERTER CORES:")
        lbl_inv.setStyleSheet("font-weight: 600; font-size: 12px; color: #A5A1B8;")
        inv_row.addWidget(lbl_inv)
        inv_row.addStretch()

        self.chk_invert = QCheckBox("Negativo")
        self.chk_invert.setStyleSheet(CHECKBOX_STYLE)
        self.chk_invert.toggled.connect(self._emit_settings_changed)
        inv_row.addWidget(self.chk_invert)
        l.addLayout(inv_row)

        if parent_layout is not None:
            parent_layout.addWidget(card)
        return card

    def _on_dither_method_changed(self, text):
        self.slider_halftone_cell.setVisible(text == "Halftone (Clusters)")
        self._emit_settings_changed()

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
        self.progress_export.setRange(0, 0)
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

    def update_presets_list(self, presets_list, current="Fotorealista"):
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        self.combo_presets.addItems(presets_list)
        if current in presets_list:
            self.combo_presets.setCurrentText(current)
        self.combo_presets.blockSignals(False)

    def _collect_transforms_config(self):
        return [
            {
                "id": "brightness_contrast",
                "enabled": self.transform_cards["brightness_contrast"].is_enabled(),
                "params": {
                    "brightness": int(self.slider_bright.value()),
                    "contrast": int(self.slider_contrast.value()),
                },
            },
            {
                "id": "channel_mixing",
                "enabled": self.transform_cards["channel_mixing"].is_enabled(),
                "params": {
                    "r_weight": round(float(self.slider_mix_r.value()), 2),
                    "g_weight": round(float(self.slider_mix_g.value()), 2),
                    "b_weight": round(float(self.slider_mix_b.value()), 2),
                },
            },
            {
                "id": "clahe",
                "enabled": self.transform_cards["clahe"].is_enabled(),
                "params": {
                    "clip_limit": round(float(self.slider_clahe_clip.value()), 2),
                    "tile_size": int(self.slider_clahe_tile.value()),
                },
            },
            {
                "id": "gamma",
                "enabled": self.transform_cards["gamma"].is_enabled(),
                "params": {
                    "gamma": round(float(self.slider_gamma.value()), 2),
                },
            },
            {
                "id": "density",
                "enabled": self.transform_cards["density"].is_enabled(),
                "params": {
                    "level": int(self.slider_density.value()),
                },
            },
            {
                "id": "sharpen",
                "enabled": self.transform_cards["sharpen"].is_enabled(),
                "params": {
                    "amount": int(self.slider_sharpen.value()),
                    "high_pass": self.chk_sharpen_hp.isChecked(),
                },
            },
            {
                "id": "bilateral",
                "enabled": self.transform_cards["bilateral"].is_enabled(),
                "params": {
                    "passes": int(self.slider_bilateral_passes.value()),
                    "sigma": int(self.slider_bilateral_sigma.value()),
                },
            },
            {
                "id": "tone_clamp",
                "enabled": self.transform_cards["tone_clamp"].is_enabled(),
                "params": {
                    "black_clamp": int(self.slider_black_clamp.value()),
                    "white_clamp": int(self.slider_white_clamp.value()),
                },
            },
            {
                "id": "quantize",
                "enabled": self.transform_cards["quantize"].is_enabled(),
                "params": {
                    "levels": int(self.combo_quantize_levels.currentData()),
                    "softness": int(self.slider_quantize_softness.value()),
                    "mode": str(self.combo_quantize_mode.currentData()),
                },
            },
            {
                "id": "cleanup",
                "enabled": self.transform_cards["cleanup"].is_enabled(),
                "params": {
                    "method": str(self.combo_cleanup_method.currentData()),
                    "kernel_size": int(self.combo_cleanup_kernel.currentData()),
                },
            },
        ]

    def get_all_settings(self):
        w, h = self.aspect_lock.get_dimensions()
        return {
            "keep_native_resolution": self.chk_keep_native_res.isChecked(),
            "width_mm": w,
            "height_mm": h,
            "target_dpi": int(self.slider_dpi.value()),
            "background": "Preto" if self.rb_bg_black.isChecked() else "Branco",
            "dither_method": self.combo_method.currentText(),
            "halftone_cell": int(self.slider_halftone_cell.value()),
            "invert_colors": self.chk_invert.isChecked(),
            "transforms": self._collect_transforms_config(),
        }

    def _set_combo_by_data(self, combo: QComboBox, data_val):
        for i in range(combo.count()):
            if combo.itemData(i) == data_val:
                combo.setCurrentIndex(i)
                return

    def apply_preset_settings(self, s: dict):
        self._suppress_signals = True
        try:
            if "keep_native_resolution" in s:
                checked = bool(s["keep_native_resolution"])
                self.chk_keep_native_res.setChecked(checked)
                self.aspect_lock.setEnabled(not checked)
                self.slider_dpi.setEnabled(not checked)
            if "target_dpi" in s:
                self.slider_dpi.setValue(s["target_dpi"])
            if "background" in s:
                if s["background"] == "Preto":
                    self.rb_bg_black.setChecked(True)
                else:
                    self.rb_bg_white.setChecked(True)
            if "dither_method" in s:
                idx = self.combo_method.findText(s["dither_method"])
                if idx >= 0:
                    self.combo_method.setCurrentIndex(idx)
                self.slider_halftone_cell.setVisible(self.combo_method.currentText() == "Halftone (Clusters)")
            if "halftone_cell" in s:
                self.slider_halftone_cell.setValue(s["halftone_cell"])
            if "invert_colors" in s:
                self.chk_invert.setChecked(bool(s["invert_colors"]))

            transforms_cfg = normalize_transforms_config(s)
            by_id = {entry["id"]: entry for entry in transforms_cfg}

            # 1. Brilho & Contraste
            e = by_id["brightness_contrast"]
            self.slider_bright.setValue(e["params"].get("brightness", 50))
            self.slider_contrast.setValue(e["params"].get("contrast", 50))
            self.transform_cards["brightness_contrast"].set_enabled_silent(e["enabled"], sync_expand=False)

            # 2. Mixagem de Canais
            e = by_id["channel_mixing"]
            self.slider_mix_r.setValue(e["params"].get("r_weight", 0.6))
            self.slider_mix_g.setValue(e["params"].get("g_weight", 0.3))
            self.slider_mix_b.setValue(e["params"].get("b_weight", 0.1))
            self.transform_cards["channel_mixing"].set_enabled_silent(e["enabled"], sync_expand=False)

            # 3. CLAHE
            e = by_id["clahe"]
            self.slider_clahe_clip.setValue(e["params"].get("clip_limit", 2.0))
            self.slider_clahe_tile.setValue(e["params"].get("tile_size", 8))
            self.transform_cards["clahe"].set_enabled_silent(e["enabled"], sync_expand=False)

            # 4. Gama
            e = by_id["gamma"]
            self.slider_gamma.setValue(e["params"].get("gamma", 1.2))
            self.transform_cards["gamma"].set_enabled_silent(e["enabled"], sync_expand=False)

            # 5. Densidade
            e = by_id["density"]
            self.slider_density.setValue(e["params"].get("level", 1))
            self.transform_cards["density"].set_enabled_silent(e["enabled"], sync_expand=False)

            # 6. Nitidez
            e = by_id["sharpen"]
            self.slider_sharpen.setValue(e["params"].get("amount", 85))
            self.chk_sharpen_hp.setChecked(bool(e["params"].get("high_pass", True)))
            self.transform_cards["sharpen"].set_enabled_silent(e["enabled"], sync_expand=False)

            # 7. Bilateral
            e = by_id["bilateral"]
            self.slider_bilateral_passes.setValue(e["params"].get("passes", 3))
            self.slider_bilateral_sigma.setValue(e["params"].get("sigma", 45))
            self.transform_cards["bilateral"].set_enabled_silent(e["enabled"], sync_expand=False)

            # 8. Trava de Extremos
            e = by_id["tone_clamp"]
            self.slider_black_clamp.setValue(e["params"].get("black_clamp", 20))
            self.slider_white_clamp.setValue(e["params"].get("white_clamp", 240))
            self.transform_cards["tone_clamp"].set_enabled_silent(e["enabled"], sync_expand=False)

            # 9. Quantização Suave
            e = by_id["quantize"]
            self._set_combo_by_data(self.combo_quantize_levels, int(e["params"].get("levels", 4)))
            self.slider_quantize_softness.setValue(e["params"].get("softness", 35))
            self._set_combo_by_data(self.combo_quantize_mode, str(e["params"].get("mode", "kmeans")))
            self.transform_cards["quantize"].set_enabled_silent(e["enabled"], sync_expand=False)

            # 10. Limpeza
            e = by_id["cleanup"]
            self._set_combo_by_data(self.combo_cleanup_method, str(e["params"].get("method", "morph_close_open")))
            self._set_combo_by_data(self.combo_cleanup_kernel, int(e["params"].get("kernel_size", 3)))
            self.transform_cards["cleanup"].set_enabled_silent(e["enabled"], sync_expand=False)
        finally:
            self._suppress_signals = False

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
