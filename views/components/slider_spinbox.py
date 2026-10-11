from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QSpinBox,
    QDoubleSpinBox, QPushButton
)


class SliderSpinBox(QWidget):
    """Componente composto: Label + Slider + SpinBox + Botão Reset (↺)"""
    valueChanged = Signal(float)

    def __init__(
        self,
        title: str,
        min_val: float,
        max_val: float,
        default_val: float,
        step: float = 1,
        decimals: int = 0,
        suffix: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.default_val = default_val
        self.decimals = decimals
        self.is_float = decimals > 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # Top row: Title + Value SpinBox + Reset Button
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-weight: 600; font-size: 12px; color: #A5A1B8;")
        header_row.addWidget(self.lbl_title)

        header_row.addStretch()

        if self.is_float:
            self.spin = QDoubleSpinBox()
            self.spin.setDecimals(decimals)
            self.spin.setSingleStep(step)
            self.spin.setRange(min_val, max_val)
            self.spin.setValue(default_val)
        else:
            self.spin = QSpinBox()
            self.spin.setSingleStep(int(step))
            self.spin.setRange(int(min_val), int(max_val))
            self.spin.setValue(int(default_val))

        if suffix:
            self.spin.setSuffix(f" {suffix}")
        self.spin.setFixedWidth(75)
        self.spin.setAlignment(Qt.AlignRight)
        header_row.addWidget(self.spin)

        # Reset button
        self.btn_reset = QPushButton("↺")
        self.btn_reset.setToolTip(f"Restaurar padrão ({default_val}{suffix})")
        self.btn_reset.setFixedSize(24, 24)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #1F1C2E;
                border: 1px solid #2D2845;
                border-radius: 4px;
                color: #A5A1B8;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2D2845;
                color: #C084FC;
                border-color: #C084FC;
            }
        """)
        self.btn_reset.clicked.connect(self.reset)
        header_row.addWidget(self.btn_reset)

        layout.addLayout(header_row)

        # Bottom row: Slider
        self.slider = QSlider(Qt.Horizontal)
        if self.is_float:
            self.slider_multiplier = 10 ** decimals
            self.slider.setRange(int(min_val * self.slider_multiplier), int(max_val * self.slider_multiplier))
            self.slider.setValue(int(default_val * self.slider_multiplier))
        else:
            self.slider_multiplier = 1
            self.slider.setRange(int(min_val), int(max_val))
            self.slider.setValue(int(default_val))

        layout.addWidget(self.slider)

        # Connect signals
        self.slider.valueChanged.connect(self._on_slider_changed)
        self.spin.valueChanged.connect(self._on_spin_changed)

    def _on_slider_changed(self, val):
        real_val = val / self.slider_multiplier if self.is_float else val
        self.spin.blockSignals(True)
        self.spin.setValue(real_val)
        self.spin.blockSignals(False)
        self.valueChanged.emit(float(real_val))

    def _on_spin_changed(self, val):
        slider_val = int(round(val * self.slider_multiplier)) if self.is_float else int(val)
        self.slider.blockSignals(True)
        self.slider.setValue(slider_val)
        self.slider.blockSignals(False)
        self.valueChanged.emit(float(val))

    def value(self):
        return self.spin.value()

    def setValue(self, val):
        val = max(self.min_val, min(self.max_val, val))
        self.spin.setValue(val)
        # Sinais cuidarão do slider e emissão

    def reset(self):
        self.setValue(self.default_val)
