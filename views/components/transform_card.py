from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QPushButton,
    QWidget,
)


class TransformCard(QFrame):
    """Card modular colapsável para uma transformação do pipeline.

    Cada card possui:
    - Checkbox mestre (ON/OFF) no cabeçalho
    - Badge compacto com resumo dos parâmetros atuais
    - Botão ▾ / ▸ para expandir/recolher os controles
    - Área de corpo onde os sliders/combos específicos da transformação são inseridos
    """

    changed = Signal()

    def __init__(self, transform_id: str, title: str, default_enabled: bool = False, parent=None):
        super().__init__(parent)
        self.transform_id = transform_id
        self._expanded = bool(default_enabled)
        self._summary_fn = None

        self.setObjectName("TransformCard")
        self._apply_card_style(default_enabled)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 7, 10, 7)
        root.setSpacing(6)

        # Cabeçalho
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        self.chk_enabled = QCheckBox(title)
        self.chk_enabled.setChecked(default_enabled)
        self.chk_enabled.setStyleSheet("""
            QCheckBox {
                color: #F8FAFC;
                font-size: 12px;
                font-weight: 600;
                spacing: 6px;
            }
            QCheckBox:!checked {
                color: #8E88A8;
                font-weight: 500;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border-radius: 4px;
                border: 1px solid #3B3459;
                background-color: #1F1C2E;
            }
            QCheckBox::indicator:checked {
                background-color: #A855F7;
                border-color: #C084FC;
            }
        """)
        self.chk_enabled.toggled.connect(self._on_enabled_toggled)
        header.addWidget(self.chk_enabled)

        header.addStretch()

        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("color: #948EB0; font-size: 10px; font-weight: 500;")
        header.addWidget(self.lbl_summary)

        self.btn_expand = QPushButton("▾" if self._expanded else "▸")
        self.btn_expand.setFixedSize(22, 22)
        self.btn_expand.setToolTip("Expandir / Recolher ajustes")
        self.btn_expand.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: #A5A1B8;
                font-size: 12px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #242036;
                border-color: #2D2845;
                color: #C084FC;
            }
        """)
        self.btn_expand.clicked.connect(self._on_toggle_expand)
        header.addWidget(self.btn_expand)

        root.addLayout(header)

        # Corpo colapsável
        self.body_widget = QWidget()
        self.body_widget.setStyleSheet("background-color: transparent;")
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(4, 4, 0, 2)
        self.body_layout.setSpacing(5)
        self.body_widget.setVisible(self._expanded)
        self.body_widget.setEnabled(default_enabled)

        root.addWidget(self.body_widget)

    def _apply_card_style(self, active: bool):
        border_color = "#7E22CE" if active else "#2D2845"
        bg_color = "#1B182B" if active else "#14121F"
        self.setStyleSheet(f"""
            QFrame#TransformCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)

    def _on_enabled_toggled(self, checked: bool):
        self._apply_card_style(checked)
        self.body_widget.setEnabled(checked)
        self.set_expanded(checked)
        self.refresh_summary()
        self.changed.emit()

    def _on_toggle_expand(self):
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool):
        self._expanded = bool(expanded)
        self.body_widget.setVisible(self._expanded)
        self.btn_expand.setText("▾" if self._expanded else "▸")

    def is_expanded(self) -> bool:
        return self._expanded

    def is_enabled(self) -> bool:
        return self.chk_enabled.isChecked()

    def set_enabled_silent(self, enabled: bool, sync_expand: bool = True):
        self.chk_enabled.blockSignals(True)
        self.chk_enabled.setChecked(bool(enabled))
        self.chk_enabled.blockSignals(False)
        self._apply_card_style(bool(enabled))
        self.body_widget.setEnabled(bool(enabled))
        if sync_expand:
            self.set_expanded(bool(enabled))
        self.refresh_summary()

    def set_summary_fn(self, fn):
        self._summary_fn = fn
        self.refresh_summary()

    def refresh_summary(self):
        if self._summary_fn is None:
            return
        try:
            text = self._summary_fn()
            self.lbl_summary.setText(text if self.is_enabled() else "OFF")
        except Exception:
            self.lbl_summary.setText("")

    def notify_param_changed(self, *args):
        self.refresh_summary()
        self.changed.emit()
