from __future__ import annotations

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class CameraViewWidget(QWidget):
    """运行看板左侧相机画面显示区。

    目前用于演示图像区域、ROI 框和状态提示；后续可在此接入真实相机取流。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("cameraView")
        self.setMinimumSize(520, 360)
        self.rois: list[tuple[int, int, int, int]] = []
        self.status_text = "等待相机画面"

    def set_rois(self, rois: list[tuple[int, int, int, int]]) -> None:
        self.rois = rois
        self.update()

    def set_status_text(self, text: str) -> None:
        self.status_text = text
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#111111"))

        # 画中心十字线，模拟相机取景辅助线。
        center = self.rect().center()
        pen = QPen(QColor("#3c3c3c"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(center.x(), 0, center.x(), self.height())
        painter.drawLine(0, center.y(), self.width(), center.y())

        font = QFont("Microsoft YaHei", 13)
        painter.setFont(font)
        painter.setPen(QColor("#9d9d9d"))
        painter.drawText(
            self.rect().adjusted(12, 12, -12, -12),
            Qt.AlignmentFlag.AlignCenter,
            self.status_text,
        )

        # 插入点：接入相机 SDK 后，这里可以改为绘制真实图像或显示 QImage。
        roi_pen = QPen(QColor("#4ec9b0"))
        roi_pen.setWidth(2)
        painter.setPen(roi_pen)
        for index, (x, y, width, height) in enumerate(self.rois):
            painter.drawRect(QRect(x, y, width, height))
            painter.drawText(x + 4, y + 16, f"ROI-{index + 1}")
