"""USB camera helpers built on OpenCV."""

from __future__ import annotations

import platform
from dataclasses import dataclass

import cv2


class CameraError(RuntimeError):
    """Raised when a camera cannot be opened or read."""


@dataclass
class CameraInfo:
    index: int
    description: str = ""


def _backend_flag() -> int:
    return cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY


def list_cameras(max_index: int = 10) -> list[CameraInfo]:
    """Probe camera indices and return the ones that open successfully."""
    cameras: list[CameraInfo] = []
    description_prop = getattr(cv2, "CAP_PROP_DEVICE_DESCRIPTION", None)
    for index in range(max_index):
        cap = cv2.VideoCapture(index, _backend_flag())
        try:
            if cap.isOpened():
                description = ""
                if description_prop is not None:
                    value = cap.get(description_prop)
                    if value:
                        description = str(value)
                cameras.append(CameraInfo(index=index, description=description or "USB Camera"))
        finally:
            cap.release()
    return cameras


class Camera:
    """Thin wrapper around cv2.VideoCapture for a USB/web camera."""

    def __init__(self, index: int = 0, width: int = 1280, height: int = 720):
        self.index = index
        self.width = width
        self.height = height
        self._cap = None

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def open(self) -> "Camera":
        if self.is_open:
            return self
        self._cap = cv2.VideoCapture(self.index, _backend_flag())
        if not self._cap.isOpened():
            raise CameraError(
                f"Could not open camera {self.index}. Use --list-cameras or try --camera N."
            )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return self

    def read(self) -> object:
        if not self.is_open:
            self.open()
        ok, frame = self._cap.read()
        if not ok or frame is None:
            raise CameraError(f"Failed to read a frame from camera {self.index}.")
        return frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
