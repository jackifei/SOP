from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPixmap


class ImageHub(QObject):
    """跨页面共享当前相机/本地图像。"""

    image_changed = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self._pixmap: QPixmap | None = None

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.image_changed.emit(pixmap)

    def current_pixmap(self) -> QPixmap | None:
        return self._pixmap


image_hub = ImageHub()
