"""Gesture classification from hand landmarks or OpenCV contours."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from math import hypot

import cv2
import numpy as np

# MediaPipe hand landmark indices.
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = range(1, 5)
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = range(5, 9)
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = range(9, 13)
RING_MCP, RING_PIP, RING_DIP, RING_TIP = range(13, 17)
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = range(17, 21)

HAND_CONNECTIONS = (
    (WRIST, THUMB_CMC),
    (THUMB_CMC, THUMB_MCP),
    (THUMB_MCP, THUMB_IP),
    (THUMB_IP, THUMB_TIP),
    (WRIST, INDEX_MCP),
    (INDEX_MCP, INDEX_PIP),
    (INDEX_PIP, INDEX_DIP),
    (INDEX_DIP, INDEX_TIP),
    (WRIST, MIDDLE_MCP),
    (MIDDLE_MCP, MIDDLE_PIP),
    (MIDDLE_PIP, MIDDLE_DIP),
    (MIDDLE_DIP, MIDDLE_TIP),
    (WRIST, RING_MCP),
    (RING_MCP, RING_PIP),
    (RING_PIP, RING_DIP),
    (RING_DIP, RING_TIP),
    (WRIST, PINKY_MCP),
    (PINKY_MCP, PINKY_PIP),
    (PINKY_PIP, PINKY_DIP),
    (PINKY_DIP, PINKY_TIP),
)

FINGER_JOINTS = {
    "index": (INDEX_MCP, INDEX_PIP, INDEX_TIP),
    "middle": (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP),
    "ring": (RING_MCP, RING_PIP, RING_TIP),
    "pinky": (PINKY_MCP, PINKY_PIP, PINKY_TIP),
}


class Gesture(IntEnum):
    UNKNOWN = 0
    FIST = 1
    OPEN_PALM = 2
    THUMBS_UP = 3
    PEACE = 4
    POINTING = 5
    OK = 6
    ILY = 7


GESTURE_LABELS = {
    Gesture.UNKNOWN: "Unknown",
    Gesture.FIST: "Fist",
    Gesture.OPEN_PALM: "Open Palm",
    Gesture.THUMBS_UP: "Thumbs Up",
    Gesture.PEACE: "Peace",
    Gesture.POINTING: "Pointing",
    Gesture.OK: "OK",
    Gesture.ILY: "I Love You",
}


def hand_frame(landmarks: np.ndarray) -> tuple[np.ndarray, float]:
    """Return the hand's up vector and size from wrist to middle MCP."""
    up = np.asarray(landmarks[MIDDLE_MCP], dtype=float) - np.asarray(landmarks[WRIST], dtype=float)
    size = float(np.linalg.norm(up))
    if size < 1e-9:
        return np.array([0.0, -1.0]), 1.0
    return up / size, size


def is_finger_extended(
    landmarks: np.ndarray,
    finger: str,
    up: np.ndarray | None = None,
    size: float | None = None,
) -> bool:
    """A finger is extended when its tip is clearly ahead of its PIP along hand-up."""
    if up is None or size is None:
        up, size = hand_frame(landmarks)
    mcp, pip, tip = FINGER_JOINTS[finger]
    tip_from_pip = np.asarray(landmarks[tip], dtype=float) - np.asarray(landmarks[pip], dtype=float)
    return float(np.dot(tip_from_pip, up)) > 0.18 * size


def is_thumb_extended(landmarks: np.ndarray, size: float | None = None) -> bool:
    """The thumb is extended when its tip is farther from the index MCP than its IP."""
    if size is None:
        _, size = hand_frame(landmarks)
    index_mcp = np.asarray(landmarks[INDEX_MCP], dtype=float)
    tip = np.asarray(landmarks[THUMB_TIP], dtype=float)
    ip = np.asarray(landmarks[THUMB_IP], dtype=float)
    return np.linalg.norm(tip - index_mcp) > np.linalg.norm(ip - index_mcp) + 0.05 * size


def extended_fingers(landmarks: np.ndarray) -> dict[str, bool]:
    up, size = hand_frame(landmarks)
    return {
        "thumb": is_thumb_extended(landmarks, size),
        "index": is_finger_extended(landmarks, "index", up, size),
        "middle": is_finger_extended(landmarks, "middle", up, size),
        "ring": is_finger_extended(landmarks, "ring", up, size),
        "pinky": is_finger_extended(landmarks, "pinky", up, size),
    }


def count_extended_fingers(landmarks: np.ndarray) -> int:
    return sum(extended_fingers(landmarks).values())


def classify_landmarks(landmarks: np.ndarray) -> Gesture:
    """Classify a 21-point hand landmark array into a named gesture."""
    ext = extended_fingers(landmarks)
    _, size = hand_frame(landmarks)
    thumb_tip = np.asarray(landmarks[THUMB_TIP], dtype=float)
    index_tip = np.asarray(landmarks[INDEX_TIP], dtype=float)
    thumb_index_gap = float(np.linalg.norm(thumb_tip - index_tip))

    if ext["middle"] and ext["ring"] and not ext["index"] and thumb_index_gap < 0.22 * size:
        return Gesture.OK
    if all(ext.values()):
        return Gesture.OPEN_PALM
    if ext["thumb"] and ext["index"] and ext["pinky"] and not ext["middle"] and not ext["ring"]:
        return Gesture.ILY
    if ext["index"] and ext["middle"] and not ext["ring"] and not ext["pinky"]:
        return Gesture.PEACE
    if ext["index"] and not ext["middle"] and not ext["ring"] and not ext["pinky"]:
        return Gesture.POINTING
    if ext["thumb"] and not ext["index"] and not ext["middle"] and not ext["ring"] and not ext["pinky"]:
        return Gesture.THUMBS_UP
    if not any(ext.values()):
        return Gesture.FIST
    return Gesture.UNKNOWN


@dataclass
class ContourGesture:
    gesture: Gesture
    finger_count: int
    solidity: float


def classify_contour(contour: np.ndarray) -> ContourGesture:
    """Classify a hand contour using convexity defects (OpenCV fallback backend)."""
    if contour is None or len(contour) < 5:
        return ContourGesture(Gesture.UNKNOWN, 0, 0.0)

    area = float(cv2.contourArea(contour))
    hull_pts = cv2.convexHull(contour)
    hull_area = float(cv2.contourArea(hull_pts))
    solidity = area / hull_area if hull_area > 0 else 0.0
    x, y, w, h = cv2.boundingRect(contour)
    extent = area / (w * h) if w and h else 0.0
    diag = hypot(w, h)

    hull_idx = cv2.convexHull(contour, returnPoints=False)
    defects = cv2.convexityDefects(contour, hull_idx)
    gaps = 0
    if defects is not None:
        for _, _, _, depth in defects[:, 0]:
            if depth > max(12.0, 0.15 * diag):
                gaps += 1

    if solidity > 0.82 and extent > 0.45:
        return ContourGesture(Gesture.FIST, 0, solidity)

    fingers = gaps + 1
    if fingers >= 5:
        return ContourGesture(Gesture.OPEN_PALM, 5, solidity)
    if fingers == 2:
        return ContourGesture(Gesture.PEACE, 2, solidity)
    if fingers == 1:
        return ContourGesture(Gesture.POINTING, 1, solidity)
    return ContourGesture(Gesture.UNKNOWN, fingers, solidity)
