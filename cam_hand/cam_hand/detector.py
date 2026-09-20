"""Hand detection backends: MediaPipe Tasks/legacy with an OpenCV skin fallback."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import cv2
import numpy as np

from cam_hand.gestures import (
    GESTURE_LABELS,
    Gesture,
    classify_contour,
    classify_landmarks,
    count_extended_fingers,
)

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - depends on local install
    mp = None

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"


class Backend(str, Enum):
    AUTO = "auto"
    MEDIAPIPE = "mediapipe"
    OPENCV = "opencv"


@dataclass
class HandResult:
    gesture: Gesture = Gesture.UNKNOWN
    landmarks: np.ndarray | None = None
    handedness: str | None = None
    box: tuple[int, int, int, int] | None = None
    mask: np.ndarray | None = None
    contour: np.ndarray | None = None
    finger_count: int = 0
    backend: str = "none"

    @property
    def label(self) -> str:
        if self.gesture == Gesture.UNKNOWN and self.finger_count:
            return f"{self.finger_count} fingers"
        return GESTURE_LABELS[self.gesture]


def skin_mask(frame: np.ndarray) -> np.ndarray:
    """Create a binary skin mask using HSV plus YCrCb ranges."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    ycr = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    hsv_mask = cv2.inRange(hsv, (0, 35, 50), (20, 175, 255)) | cv2.inRange(
        hsv, (170, 35, 50), (180, 175, 255)
    )
    ycr_mask = cv2.inRange(ycr, (0, 130, 80), (255, 180, 130))
    mask = cv2.bitwise_and(hsv_mask, ycr_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def _plausible_hand_box(x: int, y: int, w: int, h: int, frame_w: int, frame_h: int) -> bool:
    """Reject skin blobs that touch the frame edge or have an unlikely shape."""
    margin = 6
    if x <= margin or y <= margin or x + w >= frame_w - margin or y + h >= frame_h - margin:
        return False
    if w <= 0 or h <= 0:
        return False
    aspect = w / h
    return 0.4 <= aspect <= 2.6


class HandDetector:
    """Detect one hand per frame and classify its gesture."""

    def __init__(
        self,
        backend: str | Backend = Backend.AUTO,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        max_num_hands: int = 1,
    ):
        self._requested = Backend(backend)
        self._min_detection_confidence = min_detection_confidence
        self._min_tracking_confidence = min_tracking_confidence
        self._max_num_hands = max_num_hands
        self._hand_landmarker = None
        self._legacy_hands = None
        self._frame_counter = 0

        if self._requested == Backend.MEDIAPIPE and mp is None:
            raise RuntimeError(
                "The mediapipe backend needs MediaPipe. Install it with: pip install mediapipe"
            )
        if self._requested == Backend.OPENCV or mp is None:
            self.backend = Backend.OPENCV
        else:
            self._setup_mediapipe()
            if self._hand_landmarker is None and self._legacy_hands is None:
                self.backend = Backend.OPENCV
            else:
                self.backend = Backend.MEDIAPIPE


    def _setup_mediapipe(self) -> None:
        self._hand_landmarker = None
        self._legacy_hands = None

        # MediaPipe >= 1.0 uses the Tasks API and an external .task model file.
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision
            from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode as _VisionRunningMode

            if MODEL_PATH.exists():
                base_options = mp_python.BaseOptions(model_asset_path=str(MODEL_PATH))
                options = mp_vision.HandLandmarkerOptions(
                    base_options=base_options,
                    running_mode=_VisionRunningMode.VIDEO,
                    num_hands=self._max_num_hands,
                    min_hand_detection_confidence=self._min_detection_confidence,
                    min_hand_presence_confidence=self._min_detection_confidence,
                    min_tracking_confidence=self._min_tracking_confidence,
                )
                self._hand_landmarker = mp_vision.HandLandmarker.create_from_options(options)
                self._mp_image_format = mp.ImageFormat.SRGB
                return
        except Exception as exc:  # keep the OpenCV fallback available
            print(f"MediaPipe Tasks init failed, using fallback: {exc}")
            self._hand_landmarker = None

        # MediaPipe < 1.0 exposes the legacy solutions API with a bundled model.
        try:
            hands = mp.solutions.hands
            self._legacy_hands = hands.Hands(
                static_image_mode=False,
                max_num_hands=self._max_num_hands,
                min_detection_confidence=self._min_detection_confidence,
                min_tracking_confidence=self._min_tracking_confidence,
            )
        except Exception as exc:  # pragma: no cover - depends on mediapipe version
            print(f"MediaPipe legacy init failed, using fallback: {exc}")
            self._legacy_hands = None

    def detect(self, frame: np.ndarray) -> HandResult | None:
        if self.backend == Backend.MEDIAPIPE:
            return self._detect_mediapipe(frame)
        return self._detect_opencv(frame)

    def _detect_mediapipe(self, frame: np.ndarray) -> HandResult | None:
        if self._hand_landmarker is not None:
            return self._detect_tasks(frame)
        return self._detect_legacy(frame)

    def _detect_tasks(self, frame: np.ndarray) -> HandResult | None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=self._mp_image_format, data=rgb)
        self._frame_counter += 1
        timestamp_ms = int(self._frame_counter * 33.33)
        results = self._hand_landmarker.detect_for_video(mp_image, timestamp_ms)
        if not results.hand_landmarks:
            return None

        raw = results.hand_landmarks[0]
        height, width = frame.shape[:2]
        landmarks = np.asarray(
            [(point.x * width, point.y * height) for point in raw],
            dtype=np.float32,
        )
        handedness = None
        if results.handedness:
            handedness = results.handedness[0][0].category_name
        return self._result_from_landmarks(landmarks, handedness, width, height)

    def _detect_legacy(self, frame: np.ndarray) -> HandResult | None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._legacy_hands.process(rgb)
        if not results.multi_hand_landmarks:
            return None

        raw = results.multi_hand_landmarks[0]
        height, width = frame.shape[:2]
        landmarks = np.asarray(
            [(point.x * width, point.y * height) for point in raw.landmark],
            dtype=np.float32,
        )
        handedness = None
        if results.multi_handedness:
            handedness = results.multi_handedness[0].classification[0].label
        return self._result_from_landmarks(landmarks, handedness, width, height)

    def _result_from_landmarks(
        self,
        landmarks: np.ndarray,
        handedness: str | None,
        width: int,
        height: int,
    ) -> HandResult:
        gesture = classify_landmarks(landmarks)
        xs, ys = landmarks[:, 0], landmarks[:, 1]
        padding = 0.12 * max(float(xs.max() - xs.min()), float(ys.max() - ys.min()))
        x0 = max(0, int(xs.min() - padding))
        y0 = max(0, int(ys.min() - padding))
        x1 = min(width, int(xs.max() + padding))
        y1 = min(height, int(ys.max() + padding))

        return HandResult(
            gesture=gesture,
            landmarks=landmarks,
            handedness=handedness,
            box=(x0, y0, x1 - x0, y1 - y0),
            finger_count=count_extended_fingers(landmarks),
            backend="mediapipe",
        )

    def _detect_opencv(self, frame: np.ndarray) -> HandResult | None:
        mask = skin_mask(frame)
        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        if not contours:
            return None
        contour = max(contours, key=cv2.contourArea)
        height, width = frame.shape[:2]
        if cv2.contourArea(contour) < max(8000, 0.03 * height * width):
            return None

        x, y, w, h = cv2.boundingRect(contour)
        if not _plausible_hand_box(x, y, w, h, width, height):
            return None

        info = classify_contour(contour)
        return HandResult(
            gesture=info.gesture,
            box=(x, y, w, h),
            mask=mask,
            contour=contour,
            finger_count=info.finger_count,
            backend="opencv",
        )

    def close(self) -> None:
        # Do not drop the last reference to HandLandmarker: CPython deallocation
        # calls the native close() and hangs on Windows. The CLI exits via
        # os._exit() instead of waiting on native worker threads.
        if self._legacy_hands is not None:
            self._legacy_hands.close()
            self._legacy_hands = None





