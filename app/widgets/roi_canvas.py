from __future__ import annotations

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class RoiCanvas(QWidget):
    """ROI 画布。

    用于流程编辑页的 ROI 预览和大图编辑弹窗。
    """

    selection_changed = pyqtSignal(int)
    add_requested = pyqtSignal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("roiCanvas")
        self.setMinimumSize(320, 200)
        self.rois: list[dict] = []
        self.selected_index = -1
        self.setMouseTracking(True)

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
        painter.setPen(QColor("#555555"))
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))

        for index, roi in enumerate(self.rois):
            rect = QRect(
                int(roi.get("x", 0)),
                int(roi.get("y", 0)),
                int(roi.get("w", 0)),
                int(roi.get("h", 0)),
            )
            color = QColor("#4ec9b0") if index == self.selected_index else QColor("#3c8f7a")
            pen = QPen(color)
            pen.setWidth(3 if index == self.selected_index else 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            painter.drawText(rect.x() + 3, rect.y() + 16, roi.get("name", f"ROI-{index + 1}"))

        painter.setPen(QColor("#9d9d9d"))
        painter.drawText(
            self.rect().adjusted(12, 12, -12, -12),
            Qt.AlignmentFlag.AlignCenter,
            "点击 ROI 选中；双击空白处可新建 ROI",
        )

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        for index in range(len(self.rois) - 1, -1, -1):
            roi = self.rois[index]
            rect = QRect(
                int(roi.get("x", 0)),
                int(roi.get("y", 0)),
                int(roi.get("w", 0)),
                int(roi.get("h", 0)),
            )
            if rect.contains(event.position().toPoint()):
                self.selected_index = index
                self.update()
                self.selection_changed.emit(index)
                return
        self.selected_index = -1
        self.update()
        self.selection_changed.emit(-1)

    def mouseDoubleClickEvent(self, event) -> None:
        point = event.position().toPoint()
        self.add_requested.emit(point.x(), point.y())
