"""Real-time OpenCV window UI for the gesture app."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import cv2

from cam_hand.camera import Camera
from cam_hand.detector import HandResult
from cam_hand.gestures import HAND_CONNECTIONS, Gesture

WINDOW_NAME = "CAM Hand Gesture"
FONT = cv2.FONT_HERSHEY_SIMPLEX

GESTURE_COLORS = {
    Gesture.UNKNOWN: (220, 220, 220),
    Gesture.FIST: (80, 180, 255),
    Gesture.OPEN_PALM: (90, 220, 90),
    Gesture.THUMBS_UP: (220, 220, 60),
    Gesture.PEACE: (200, 120, 255),
    Gesture.POINTING: (255, 160, 60),
    Gesture.OK: (200, 200, 0),
    Gesture.ILY: (90, 200, 255),
}


def _text_with_background(
    frame,
    text: str,
    origin: tuple[int, int],
    scale: float,
    color,
    thickness: int = 2,
) -> None:
    (text_w, text_h), baseline = cv2.getTextSize(text, FONT, scale, thickness)
    x, y = origin
    cv2.rectangle(
        frame,
        (x - 4, y - text_h - 6),
        (x + text_w + 4, y + baseline + 2),
        (15, 15, 15),
        -1,
    )
    cv2.putText(frame, text, (x, y), FONT, scale, color, thickness, cv2.LINE_AA)


def render_frame(
    frame,
    result: HandResult | None,
    fps: float,
    camera_index: int,
    backend_name: str,
    show_help: bool,
    detect_enabled: bool,
    mirror: bool,
):
    """Draw detection overlays onto one frame and return it."""
    frame = frame.copy()
    height, width = frame.shape[:2]
    color = GESTURE_COLORS[result.gesture] if result else GESTURE_COLORS[Gesture.UNKNOWN]

    if result is not None:
        if result.box is not None:
            x, y, w, h = result.box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            label = result.label
            (text_w, text_h), _ = cv2.getTextSize(label, FONT, 0.7, 2)
            label_y = y - 14 if y - 14 > text_h + 8 else y + text_h + 10
            _text_with_background(frame, label, (x, label_y), 0.7, color)

        if result.landmarks is not None:
            points = result.landmarks.astype(int)
            for start, end in HAND_CONNECTIONS:
                cv2.line(frame, tuple(points[start]), tuple(points[end]), color, 2)
            for point in points:
                cv2.circle(frame, tuple(point), 4, (255, 255, 255), -1)
                cv2.circle(frame, tuple(point), 4, color, 1)

        if result.mask is not None and result.mask.any():
            preview = cv2.resize(result.mask, (180, 120))
            preview = cv2.cvtColor(preview, cv2.COLOR_GRAY2BGR)
            frame[height - 120 : height, width - 180 : width] = preview

    status = (
        f"FPS {fps:4.1f} | CAM {camera_index} | {backend_name} | "
        f"DETECT {'ON' if detect_enabled else 'OFF'} | MIRROR {'ON' if mirror else 'OFF'}"
    )
    _text_with_background(frame, status, (12, 34), 0.55, (230, 230, 230), 2)

    if show_help:
        _text_with_background(
            frame,
            "[Q/Esc] Quit  [D] Detect  [R] Mirror  [S] Screenshot  [H] Help",
            (12, height - 18),
            0.5,
            (200, 200, 200),
            2,
        )
        _text_with_background(
            frame,
            "[0-9] Switch camera",
            (12, height - 44),
            0.5,
            (200, 200, 200),
            2,
        )
    return frame


class GestureApp:
    """Live camera loop with keyboard controls."""

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 1280,
        height: int = 720,
        mirror: bool = True,
        detector=None,
    ):
        self.camera = Camera(camera_index, width, height)
        self.detector = detector
        self.mirror = mirror
        self.detect_enabled = True
        self.show_help = True
        self._fps = 0.0
        self._last_frame_time = time.perf_counter()
        self._last_frame = None

    def run(self) -> None:
        self.camera.open()
        print(
            f"Camera {self.camera.index} opened. Backend: {self.detector.backend.value}. "
            "Press Q or Esc to quit."
        )
        try:
            while True:
                frame = self.camera.read()
                now = time.perf_counter()
                elapsed = max(now - self._last_frame_time, 1e-6)
                instant_fps = 1.0 / elapsed
                self._fps = self._fps * 0.9 + instant_fps * 0.1
                self._last_frame_time = now

                if self.mirror:
                    frame = cv2.flip(frame, 1)
                self._last_frame = frame

                result = self.detector.detect(frame) if self.detect_enabled else None
                annotated = render_frame(
                    frame,
                    result,
                    self._fps,
                    self.camera.index,
                    self.detector.backend.value,
                    self.show_help,
                    self.detect_enabled,
                    self.mirror,
                )
                cv2.imshow(WINDOW_NAME, annotated)

                key = cv2.waitKey(1) & 0xFF
                if not self._handle_key(key):
                    break
        finally:
            self.close()

    def _handle_key(self, key: int) -> bool:
        if key in (ord("q"), 27):
            return False
        if key == ord("h"):
            self.show_help = not self.show_help
        elif key == ord("d"):
            self.detect_enabled = not self.detect_enabled
        elif key == ord("r"):
            self.mirror = not self.mirror
        elif key == ord("s"):
            self._save_screenshot()
        elif ord("0") <= key <= ord("9"):
            self._switch_camera(key - ord("0"))
        return True

    def _switch_camera(self, index: int) -> None:
        if index == self.camera.index:
            return
        self.camera.release()
        self.camera.index = index
        try:
            self.camera.open()
            print(f"Switched to camera {index}.")
        except Exception as exc:  # keep the app alive if the new camera fails
            print(f"Could not switch to camera {index}: {exc}")
            self.camera.index = index

    def _save_screenshot(self) -> None:
        if self._last_frame is None:
            return
        directory = Path("screenshots")
        directory.mkdir(exist_ok=True)
        filename = directory / f"hand_{datetime.now():%Y%m%d_%H%M%S_%f}.png"
        cv2.imwrite(str(filename), self._last_frame)
        print(f"Screenshot saved: {filename}")

    def close(self) -> None:
        self.camera.release()
        cv2.destroyAllWindows()
