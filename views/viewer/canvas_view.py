from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPixmap, QPainter, QImage, QColor
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem
)


class CanvasView(QGraphicsView):
    """Visualizador de imagem de alta performance baseado em QGraphicsView."""
    zoomChanged = Signal(float)       # emite a escala acumulada
    panChanged = Signal(int, int)     # emite valores dos scrollbars (h, v)

    def __init__(self, placeholder_text="Sem Imagem", parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        self.placeholder_item = QGraphicsTextItem(placeholder_text)
        self.placeholder_item.setDefaultTextColor(QColor("#5E5873"))
        self.scene.addItem(self.placeholder_item)

        self.current_zoom = 1.0
        self._syncing_pan = False
        self._syncing_zoom = False

        # Visual settings
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #171523;
                border: 1px solid #2D2845;
                border-radius: 6px;
            }
        """)

        # Connect scrollbars for pan synchronization
        self.horizontalScrollBar().valueChanged.connect(self._on_scroll_changed)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

    def set_image(self, qimg: QImage):
        if qimg is None or qimg.isNull():
            return
        pixmap = QPixmap.fromImage(qimg)
        self.pixmap_item.setPixmap(pixmap)
        self.placeholder_item.setVisible(False)
        self.scene.setSceneRect(QRectF(pixmap.rect()))

    def _update_rendering_quality(self):
        # Em zoom ampliado (> 2.0x), usamos pixelização nítida (Nearest Neighbor)
        # para que o operador de laser possa inspecionar pontos de dither individuais.
        if self.current_zoom > 2.0:
            self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        else:
            self.setRenderHint(QPainter.SmoothPixmapTransform, True)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        if angle == 0:
            return

        # Zoom suave proporcional ao scroll (~5% por clique padrão do mouse)
        steps = angle / 120.0
        factor = 1.05 ** steps
        new_zoom = max(0.05, min(50.0, self.current_zoom * factor))

        actual_factor = new_zoom / self.current_zoom
        if abs(actual_factor - 1.0) > 1e-4:
            self.current_zoom = new_zoom
            self.scale(actual_factor, actual_factor)
            self._update_rendering_quality()
            if not self._syncing_zoom:
                self.zoomChanged.emit(self.current_zoom)

    def set_zoom_absolute(self, target_zoom: float, notify: bool = False):
        if self._syncing_zoom or target_zoom <= 0:
            return
        self._syncing_zoom = True
        factor = target_zoom / self.current_zoom
        self.current_zoom = target_zoom
        self.scale(factor, factor)
        self._update_rendering_quality()
        self._syncing_zoom = False
        if notify:
            self.zoomChanged.emit(self.current_zoom)

    def sync_scroll(self, h_val: int, v_val: int):
        self._syncing_pan = True
        self.horizontalScrollBar().setValue(h_val)
        self.verticalScrollBar().setValue(v_val)
        self._syncing_pan = False

    def sync_scroll_from(self, other_canvas):
        """Sincroniza a posição de rolagem normalizada (percentual) a partir de outro CanvasView."""
        if self._syncing_pan:
            return
        self._syncing_pan = True
        try:
            other_h = other_canvas.horizontalScrollBar()
            other_v = other_canvas.verticalScrollBar()
            h_range = other_h.maximum() - other_h.minimum()
            v_range = other_v.maximum() - other_v.minimum()
            h_ratio = (other_h.value() - other_h.minimum()) / h_range if h_range > 0 else 0.0
            v_ratio = (other_v.value() - other_v.minimum()) / v_range if v_range > 0 else 0.0

            my_h = self.horizontalScrollBar()
            my_v = self.verticalScrollBar()
            my_h_range = my_h.maximum() - my_h.minimum()
            my_v_range = my_v.maximum() - my_v.minimum()
            if my_h_range > 0:
                my_h.setValue(int(round(my_h.minimum() + h_ratio * my_h_range)))
            if my_v_range > 0:
                my_v.setValue(int(round(my_v.minimum() + v_ratio * my_v_range)))
        finally:
            self._syncing_pan = False

    def _on_scroll_changed(self):
        if not self._syncing_pan:
            self.panChanged.emit(
                self.horizontalScrollBar().value(),
                self.verticalScrollBar().value()
            )

    def fit_in_view(self):
        rect = self.pixmap_item.boundingRect()
        if not rect.isEmpty():
            self.resetTransform()
            self.fitInView(rect, Qt.KeepAspectRatio)
            # Recalcula o current_zoom baseado na transformação aplicada
            self.current_zoom = self.transform().m11()
            self._update_rendering_quality()
            self.zoomChanged.emit(self.current_zoom)

    def zoom_1_to_1(self):
        self.resetTransform()
        self.current_zoom = 1.0
        self._update_rendering_quality()
        self.zoomChanged.emit(self.current_zoom)
