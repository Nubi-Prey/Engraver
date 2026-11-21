import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPixmap, QPainter, QImage, QColor, QTransform
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem
)


class CanvasView(QGraphicsView):
    """Visualizador de imagem de alta performance baseado em QGraphicsView.

    Quando `use_area_mipmaps=True` (usado no painel de simulação 1-bit):
    - `zoom >= 1.0`: exibe pixels 1:1 nítidos (FastTransformation), sem borrão.
    - `zoom < 1.0`: utiliza pirâmide de mipmaps via `cv2.INTER_AREA` + SmoothTransformation,
      eliminando efeito Moiré em padrões de dithering e preservando a densidade real da gravação.
    """

    zoomChanged = Signal(float)       # emite a escala acumulada
    panChanged = Signal(int, int)     # emite valores dos scrollbars (h, v)

    def __init__(self, placeholder_text="Sem Imagem", use_area_mipmaps: bool = False, parent=None):
        super().__init__(parent)
        self._use_area_mipmaps = bool(use_area_mipmaps)
        self._base_size = (0, 0)
        self._mipmaps = {}
        self._source_arr = None
        self._active_mipmap_level = 0

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem()
        self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
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

    def _extract_grayscale_array(self, qimg: QImage):
        gray = qimg if qimg.format() == QImage.Format_Grayscale8 else qimg.convertToFormat(QImage.Format_Grayscale8)
        w, h = gray.width(), gray.height()
        if w <= 0 or h <= 0:
            return None
        bpl = gray.bytesPerLine()
        buf = memoryview(gray.constBits()).tobytes()
        if len(buf) < h * bpl:
            return None
        return np.frombuffer(buf, dtype=np.uint8, count=h * bpl).reshape((h, bpl))[:, :w].copy()

    def _get_mipmap_pixmap(self, level: int):
        if level in self._mipmaps:
            return self._mipmaps[level]
        if level <= 0 or self._source_arr is None:
            return self._mipmaps.get(0)

        h, w = self._source_arr.shape
        factor = 1 << level
        mw = max(1, w // factor)
        mh = max(1, h // factor)
        resized = cv2.resize(self._source_arr, (mw, mh), interpolation=cv2.INTER_AREA)
        mip_qimg = QImage(resized.data, mw, mh, mw, QImage.Format_Grayscale8).copy()
        pm = QPixmap.fromImage(mip_qimg)
        self._mipmaps[level] = pm
        return pm

    def _choose_mipmap_level(self, zoom: float) -> int:
        if not self._use_area_mipmaps or zoom >= 1.0:
            return 0
        w, h = self._base_size
        min_dim = min(w, h)
        if zoom <= 0.125 and min_dim >= 32:
            return 3
        if zoom <= 0.25 and min_dim >= 16:
            return 2
        if zoom <= 0.5 and min_dim >= 8:
            return 1
        return 0

    def _apply_mipmap_level(self, level: int):
        if not self._mipmaps or self._base_size[0] <= 0 or self._base_size[1] <= 0:
            return
        if level == self._active_mipmap_level and not self.pixmap_item.pixmap().isNull():
            return
        pm = self._get_mipmap_pixmap(level)
        if pm is None or pm.isNull():
            return
        w, h = self._base_size
        self.pixmap_item.setPixmap(pm)
        if level == 0 or (pm.width() == w and pm.height() == h):
            self.pixmap_item.resetTransform()
        else:
            self.pixmap_item.setTransform(QTransform.fromScale(w / pm.width(), h / pm.height()))
        self._active_mipmap_level = level

    def set_image(self, qimg: QImage):
        if qimg is None or qimg.isNull():
            return
        pixmap = QPixmap.fromImage(qimg)
        self._base_size = (pixmap.width(), pixmap.height())
        self._mipmaps = {0: pixmap}
        self._active_mipmap_level = 0
        self._source_arr = self._extract_grayscale_array(qimg) if self._use_area_mipmaps else None

        self.pixmap_item.resetTransform()
        self.pixmap_item.setPixmap(pixmap)
        self.placeholder_item.setVisible(False)
        self.scene.setSceneRect(QRectF(0, 0, pixmap.width(), pixmap.height()))
        self._update_rendering_quality()

    def set_display_size(self, target_w: int, target_h: int):
        """Sincroniza a geometria da cena com outro canvas sem reamostrar os pixels do pixmap."""
        pixmap = self.pixmap_item.pixmap()
        if pixmap.isNull() or pixmap.width() <= 0 or pixmap.height() <= 0:
            return
        if target_w <= 0 or target_h <= 0:
            return
        sx = target_w / pixmap.width()
        sy = target_h / pixmap.height()
        self.pixmap_item.setTransform(QTransform.fromScale(sx, sy))
        self.scene.setSceneRect(QRectF(0, 0, target_w, target_h))

    def _update_rendering_quality(self):
        if self._use_area_mipmaps:
            if self.current_zoom >= 1.0:
                self._apply_mipmap_level(0)
                self.pixmap_item.setTransformationMode(Qt.FastTransformation)
                self.setRenderHint(QPainter.SmoothPixmapTransform, False)
            else:
                level = self._choose_mipmap_level(self.current_zoom)
                self._apply_mipmap_level(level)
                self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
                self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        else:
            # Painel original: suave em zoom <= 2.0x, pixel nítido em zoom > 2.0x
            if self.current_zoom > 2.0:
                self.pixmap_item.setTransformationMode(Qt.FastTransformation)
                self.setRenderHint(QPainter.SmoothPixmapTransform, False)
            else:
                self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
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
        rect = self.pixmap_item.sceneBoundingRect()
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
