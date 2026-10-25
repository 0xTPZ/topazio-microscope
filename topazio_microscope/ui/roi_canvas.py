import cv2
import numpy as np
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView


class RoiCanvas(QGraphicsView):
    """Visualizador leve que devolve ROI em coordenadas da imagem, não da tela."""

    roi_selected = Signal(int, int, int, int)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setBackgroundBrush(QColor('#0d1622'))
        self.setMinimumSize(220, 180)
        self.setDragMode(QGraphicsView.NoDrag)
        self.image_item = None
        self.selection_item = None
        self.frame = None
        self.roi = None
        self._start = None
        self._drawing = False

    def set_frame(self, frame: np.ndarray) -> None:
        if frame is None or frame.size == 0:
            return
        self.frame = frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame.ndim == 3 else frame
        fmt = QImage.Format_RGB888 if frame.ndim == 3 else QImage.Format_Grayscale8
        image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], fmt).copy()
        previous = self.roi if self.roi and self.roi[0] < frame.shape[1] and self.roi[1] < frame.shape[0] else None
        self.scene.clear()
        self.image_item = QGraphicsPixmapItem(QPixmap.fromImage(image))
        self.scene.addItem(self.image_item)
        self.scene.setSceneRect(QRectF(0, 0, image.width(), image.height()))
        self.roi = previous
        self._draw_selection()
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def clear_selection(self) -> None:
        self.roi = None
        if self.selection_item:
            self.scene.removeItem(self.selection_item)
            self.selection_item = None

    def _draw_selection(self) -> None:
        if self.selection_item:
            self.scene.removeItem(self.selection_item)
            self.selection_item = None
        if not self.roi:
            return
        x, y, width, height = self.roi
        pen = QPen(QColor('#d9aa3a')); pen.setWidth(2)
        self.selection_item = QGraphicsRectItem(QRectF(x, y, width, height))
        self.selection_item.setPen(pen)
        self.selection_item.setBrush(QBrush(Qt.NoBrush))
        self.selection_item.setZValue(10)
        self.scene.addItem(self.selection_item)

    def _scene_point(self, event):
        point = self.mapToScene(event.position().toPoint())
        rect = self.scene.sceneRect()
        return max(rect.left(), min(rect.right(), point.x())), max(rect.top(), min(rect.bottom(), point.y()))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.image_item:
            self._start = self._scene_point(event)
            self._drawing = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drawing:
            end = self._scene_point(event)
            x = int(min(self._start[0], end[0])); y = int(min(self._start[1], end[1]))
            width = max(1, int(abs(end[0] - self._start[0]))); height = max(1, int(abs(end[1] - self._start[1])))
            self.roi = (x, y, width, height)
            self._draw_selection()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drawing and event.button() == Qt.LeftButton:
            self._drawing = False
            if self.roi and self.roi[2] > 3 and self.roi[3] > 3:
                self.roi_selected.emit(*self.roi)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.scene.sceneRect().isValid():
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
