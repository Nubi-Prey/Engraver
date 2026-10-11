from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget


class LoadingSpinner(QWidget):
    """Spinner de carregamento vetorial animado com estilo Lilás Brilhante (#C084FC) e fundo #1F1C2E."""

    def __init__(self, size=18, line_width=2.5, color="#C084FC", track_color="#1F1C2E", parent=None):
        super().__init__(parent)
        self.spinner_size = size
        self.line_width = line_width
        self.color = QColor(color)
        self.track_color = QColor(track_color)
        self.angle = 0

        self.setFixedSize(size, size)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.setVisible(False)

    def _rotate(self):
        self.angle = (self.angle + 12) % 360
        self.update()

    def start(self):
        """Inicia a rotação e torna o spinner visível."""
        if not self.timer.isActive():
            self.angle = 0
            self.timer.start(25)  # ~40 FPS suave
        self.setVisible(True)

    def stop(self):
        """Para a rotação e oculta o spinner."""
        if self.timer.isActive():
            self.timer.stop()
        self.setVisible(False)

    def is_spinning(self) -> bool:
        return self.timer.isActive()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        margin = self.line_width / 2.0
        rect = QRectF(
            margin,
            margin,
            self.width() - self.line_width,
            self.height() - self.line_width,
        )

        # 1. Trilha de fundo (cinza escuro)
        pen_track = QPen(self.track_color, self.line_width)
        painter.setPen(pen_track)
        painter.drawEllipse(rect)

        # 2. Arco animado rotativo (Lilás Brilhante #C084FC)
        pen_arc = QPen(self.color, self.line_width)
        pen_arc.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_arc)

        # Qt angles em 1/16 de grau
        start_angle = int(-self.angle * 16)
        span_angle = int(100 * 16)  # Arco de 100 graus
        painter.drawArc(rect, start_angle, span_angle)
