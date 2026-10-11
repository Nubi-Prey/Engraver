from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QDoubleSpinBox, QPushButton
)


class AspectRatioLock(QWidget):
    """Controle de Largura e Altura físicas em mm com trava de proporção (🔗)."""
    dimensionsChanged = Signal(float, float)

    def __init__(self, default_w=100.0, default_h=100.0, parent=None):
        super().__init__(parent)
        self._aspect_ratio = default_w / default_h if default_h > 0 else 1.0
        self._is_locked = True
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        title_lbl = QLabel("TAMANHO FÍSICO (mm)")
        title_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #A5A1B8;")
        layout.addWidget(title_lbl)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        # Width
        lbl_w = QLabel("L:")
        lbl_w.setStyleSheet("color: #A5A1B8; font-weight: bold;")
        row.addWidget(lbl_w)

        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(0.1, 9999.0)
        self.spin_w.setDecimals(1)
        self.spin_w.setSingleStep(1.0)
        self.spin_w.setValue(default_w)
        self.spin_w.setSuffix(" mm")
        self.spin_w.setAlignment(Qt.AlignRight)
        row.addWidget(self.spin_w)

        # Lock toggle button
        self.btn_lock = QPushButton("🔗")
        self.btn_lock.setCheckable(True)
        self.btn_lock.setChecked(True)
        self.btn_lock.setFixedSize(28, 28)
        self.btn_lock.setToolTip("Bloquear proporção de aspecto (Aspect Ratio)")
        self._update_lock_style()
        self.btn_lock.clicked.connect(self._toggle_lock)
        row.addWidget(self.btn_lock)

        # Height
        lbl_h = QLabel("A:")
        lbl_h.setStyleSheet("color: #A5A1B8; font-weight: bold;")
        row.addWidget(lbl_h)

        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(0.1, 9999.0)
        self.spin_h.setDecimals(1)
        self.spin_h.setSingleStep(1.0)
        self.spin_h.setValue(default_h)
        self.spin_h.setSuffix(" mm")
        self.spin_h.setAlignment(Qt.AlignRight)
        row.addWidget(self.spin_h)

        layout.addLayout(row)

        self.spin_w.valueChanged.connect(self._on_width_changed)
        self.spin_h.valueChanged.connect(self._on_height_changed)

    def _update_lock_style(self):
        if self._is_locked:
            self.btn_lock.setText("🔗")
            self.btn_lock.setStyleSheet("""
                QPushButton {
                    background-color: #A855F7;
                    border: 1px solid #C084FC;
                    border-radius: 4px;
                    color: #F8FAFC;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #C084FC;
                }
            """)
        else:
            self.btn_lock.setText("🔓")
            self.btn_lock.setStyleSheet("""
                QPushButton {
                    background-color: #1F1C2E;
                    border: 1px solid #2D2845;
                    border-radius: 4px;
                    color: #5E5873;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #2D2845;
                    color: #A5A1B8;
                    border-color: #6366F1;
                }
            """)

    def _toggle_lock(self):
        self._is_locked = self.btn_lock.isChecked()
        self._update_lock_style()
        if self._is_locked and self.spin_h.value() > 0:
            self._aspect_ratio = self.spin_w.value() / self.spin_h.value()

    def set_aspect_ratio(self, ratio: float):
        if ratio > 0:
            self._aspect_ratio = ratio

    def set_dimensions(self, w: float, h: float):
        self._updating = True
        self.spin_w.blockSignals(True)
        self.spin_h.blockSignals(True)
        self.spin_w.setValue(w)
        self.spin_h.setValue(h)
        if h > 0:
            self._aspect_ratio = w / h
        self.spin_w.blockSignals(False)
        self.spin_h.blockSignals(False)
        self._updating = False
        self.dimensionsChanged.emit(w, h)

    def _on_width_changed(self, w: float):
        if self._updating:
            return
        if self._is_locked and self._aspect_ratio > 0:
            self._updating = True
            h = round(w / self._aspect_ratio, 1)
            self.spin_h.blockSignals(True)
            self.spin_h.setValue(h)
            self.spin_h.blockSignals(False)
            self._updating = False
        self.dimensionsChanged.emit(self.spin_w.value(), self.spin_h.value())

    def _on_height_changed(self, h: float):
        if self._updating:
            return
        if self._is_locked and self._aspect_ratio > 0:
            self._updating = True
            w = round(h * self._aspect_ratio, 1)
            self.spin_w.blockSignals(True)
            self.spin_w.setValue(w)
            self.spin_w.blockSignals(False)
            self._updating = False
        self.dimensionsChanged.emit(self.spin_w.value(), self.spin_h.value())

    def get_dimensions(self):
        return self.spin_w.value(), self.spin_h.value()
