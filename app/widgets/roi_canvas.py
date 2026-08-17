from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget


class RoiCanvas(QWidget):
    """ROI 画布。

    支持背景图像、圆形 ROI、旋转矩形 ROI，以及中心点拖拽移动。
    """

    selection_changed = pyqtSignal(int)
    add_requested = pyqtSignal(float, float)
    roi_updated = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("roiCanvas")
        self.setMinimumSize(320, 220)
        self.rois: list[dict] = []
        self.image: QPixmap | None = None
        self._zoom = 1.0
        self._pan_offset = QPointF(0.0, 0.0)
        self._cross_visible = False
        self._cross_ratio = QPointF(0.5, 0.5)
        self._panning = False
        self._last_pan_pos = QPointF(0.0, 0.0)
        self.selected_index = -1
        self.dragging_index = -1
        self.setMouseTracking(True)

    def set_image(self, pixmap: QPixmap | None) -> None:
        self.image = pixmap
        self.update()

    def set_show_cross(self, visible: bool) -> None:
        self._cross_visible = visible
        self.update()

    def center_cross(self) -> None:
        self._cross_ratio = QPointF(0.5, 0.5)
        self.update()

    def set_rois(self, rois: list[dict]) -> None:
        self.rois = rois
        self.selected_index = -1
        self.update()

    def get_rois(self) -> list[dict]:
        return self.rois

    def selected_roi(self) -> dict | None:
        if 0 <= self.selected_index < len(self.rois):
            return self.rois[self.selected_index]
        return None

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111111"))

        image_rect = self._image_rect()
        if self.image is not None and not image_rect.isNull():
            painter.drawPixmap(image_rect.toRect(), self.image)

        for index, roi in enumerate(self.rois):
            selected = index == self.selected_index
            color = QColor("#ff3b3b") if selected else QColor("#3c8f7a")
            pen = QPen(color)
            pen.setWidth(3 if selected else 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            self._draw_roi(painter, roi, image_rect)
            center = self._image_to_widget_point(self._roi_center(roi), image_rect)
            painter.setBrush(color)
            painter.drawEllipse(center, 4, 4)
            painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._cross_visible:
            cross_pen = QPen(QColor("#ff3b3b"))
            cross_pen.setStyle(Qt.PenStyle.DashLine)
            cross_pen.setWidth(1)
            painter.setPen(cross_pen)
            cross_x = image_rect.left() + image_rect.width() * self._cross_ratio.x()
            cross_y = image_rect.top() + image_rect.height() * self._cross_ratio.y()
            painter.drawLine(
                int(cross_x), int(image_rect.top()), int(cross_x), int(image_rect.bottom())
            )
            painter.drawLine(
                int(image_rect.left()), int(cross_y), int(image_rect.right()), int(cross_y)
            )

    def _image_rect(self) -> QRectF:
        if self.image is None or self.image.isNull():
            return QRectF(self.rect())
        scale = min(self.width() / self.image.width(), self.height() / self.image.height()) * self._zoom
        w = self.image.width() * scale
        h = self.image.height() * scale
        return QRectF(
            (self.width() - w) / 2.0 + self._pan_offset.x(),
            (self.height() - h) / 2.0 + self._pan_offset.y(),
            w,
            h,
        )

    def _draw_roi(self, painter: QPainter, roi: dict, image_rect: QRectF) -> None:
        shape = roi.get("shape", "rect")
        center = self._image_to_widget_point(self._roi_center(roi), image_rect)
        if shape == "circle":
            radius = float(roi.get("radius", 30)) * self._image_scale(image_rect)
            painter.drawEllipse(center, radius, radius)
            return
        width = float(roi.get("width", 160)) * self._image_scale(image_rect)
        height = float(roi.get("height", 120)) * self._image_scale(image_rect)
        angle = float(roi.get("angle", 0))
        painter.save()
        painter.translate(center)
        painter.rotate(angle)
        painter.drawRect(QRectF(-width / 2.0, -height / 2.0, width, height))
        painter.restore()

    def _image_scale(self, image_rect: QRectF) -> float:
        if self.image is None or image_rect.width() <= 0:
            return 1.0
        return image_rect.width() / self.image.width()

    def _image_to_widget_point(self, point: QPointF, image_rect: QRectF) -> QPointF:
        scale = self._image_scale(image_rect)
        return QPointF(
            image_rect.left() + point.x() * scale,
            image_rect.top() + point.y() * scale,
        )

    def _widget_to_image_point(self, point: QPointF, image_rect: QRectF) -> QPointF:
        scale = self._image_scale(image_rect)
        return QPointF(
            (point.x() - image_rect.left()) / scale,
            (point.y() - image_rect.top()) / scale,
        )

    def _roi_center(self, roi: dict) -> QPointF:
        return QPointF(float(roi.get("center_x", 0)), float(roi.get("center_y", 0)))

    def _contains(self, roi: dict, image_point: QPointF) -> bool:
        center = self._roi_center(roi)
        dx = image_point.x() - center.x()
        dy = image_point.y() - center.y()
        if roi.get("shape", "rect") == "circle":
            radius = float(roi.get("radius", 30)) + 4
            return math.hypot(dx, dy) <= radius
        angle = math.radians(-float(roi.get("angle", 0)))
        local_x = dx * math.cos(angle) - dy * math.sin(angle)
        local_y = dx * math.sin(angle) + dy * math.cos(angle)
        return abs(local_x) <= float(roi.get("width", 160)) / 2 + 4 and abs(
            local_y
        ) <= float(roi.get("height", 120)) / 2 + 4

    def _near_center(self, roi: dict, image_point: QPointF) -> bool:
        center = self._roi_center(roi)
        return math.hypot(image_point.x() - center.x(), image_point.y() - center.y()) <= 8

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._last_pan_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        image_rect = self._image_rect()
        image_point = self._widget_to_image_point(event.position(), image_rect)
        for index in range(len(self.rois) - 1, -1, -1):
            if self._near_center(self.rois[index], image_point):
                self.dragging_index = index
                self.selected_index = index
                self.selection_changed.emit(index)
                self.update()
                return
        for index in range(len(self.rois) - 1, -1, -1):
            if self._contains(self.rois[index], image_point):
                self.selected_index = index
                self.selection_changed.emit(index)
                self.update()
                return
        self.selected_index = -1
        self.selection_changed.emit(-1)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._last_pan_pos
            self._pan_offset += delta
            self._last_pan_pos = event.position()
            self.update()
            return
        if self.dragging_index < 0:
            return
        image_rect = self._image_rect()
        image_point = self._widget_to_image_point(event.position(), image_rect)
        roi = self.rois[self.dragging_index]
        roi["center_x"] = round(image_point.x(), 2)
        roi["center_y"] = round(image_point.y(), 2)
        self.update()
        self.roi_updated.emit(self.dragging_index)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = False
            self.unsetCursor()
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_index = -1

    def mouseDoubleClickEvent(self, event) -> None:
        image_rect = self._image_rect()
        image_point = self._widget_to_image_point(event.position(), image_rect)
        self.add_requested.emit(image_point.x(), image_point.y())

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        self._zoom = max(0.1, min(10.0, self._zoom * factor))
        self.update()
