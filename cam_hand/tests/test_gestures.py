import unittest

import numpy as np

from cam_hand.gestures import (
    Gesture,
    INDEX_MCP,
    INDEX_PIP,
    INDEX_TIP,
    MIDDLE_MCP,
    MIDDLE_PIP,
    MIDDLE_TIP,
    PINKY_MCP,
    PINKY_PIP,
    PINKY_TIP,
    RING_MCP,
    RING_PIP,
    RING_TIP,
    THUMB_IP,
    THUMB_MCP,
    THUMB_TIP,
    WRIST,
    classify_landmarks,
    count_extended_fingers,
)


POSITIONS = {
    "index": {
        "mcp": (0.38, 0.55),
        "pip": (0.39, 0.44),
        "extended": (0.41, 0.29),
        "curled": (0.46, 0.58),
        "ok": (0.46, 0.585),
    },
    "middle": {
        "mcp": (0.50, 0.50),
        "pip": (0.50, 0.40),
        "extended": (0.50, 0.25),
        "curled": (0.52, 0.53),
    },
    "ring": {
        "mcp": (0.62, 0.52),
        "pip": (0.63, 0.42),
        "extended": (0.65, 0.27),
        "curled": (0.64, 0.55),
    },
    "pinky": {
        "mcp": (0.72, 0.56),
        "pip": (0.73, 0.47),
        "extended": (0.75, 0.34),
        "curled": (0.74, 0.58),
    },
    "thumb": {
        "mcp": (0.52, 0.68),
        "ip": (0.45, 0.60),
        "open": (0.32, 0.45),
        "curled": (0.44, 0.58),
        "up": (0.62, 0.35),
        "ok": (0.47, 0.60),
    },
}


def build_landmarks(
    thumb="curled",
    index="extended",
    middle="extended",
    ring="extended",
    pinky="extended",
    ok=False,
):
    lm = np.zeros((21, 2), dtype=float)
    lm[WRIST] = (0.5, 0.9)
    lm[MIDDLE_MCP] = POSITIONS["middle"]["mcp"]
    lm[MIDDLE_PIP] = POSITIONS["middle"]["pip"]
    lm[MIDDLE_TIP] = POSITIONS["middle"][middle]
    lm[INDEX_MCP] = POSITIONS["index"]["mcp"]
    lm[INDEX_PIP] = POSITIONS["index"]["pip"]
    lm[INDEX_TIP] = POSITIONS["index"]["ok" if ok else index]
    lm[RING_MCP] = POSITIONS["ring"]["mcp"]
    lm[RING_PIP] = POSITIONS["ring"]["pip"]
    lm[RING_TIP] = POSITIONS["ring"][ring]
    lm[PINKY_MCP] = POSITIONS["pinky"]["mcp"]
    lm[PINKY_PIP] = POSITIONS["pinky"]["pip"]
    lm[PINKY_TIP] = POSITIONS["pinky"][pinky]
    lm[THUMB_MCP] = POSITIONS["thumb"]["mcp"]
    lm[THUMB_IP] = POSITIONS["thumb"]["ip"]
    lm[THUMB_TIP] = POSITIONS["thumb"]["ok" if ok else thumb]
    return lm


class LandmarkGestureTests(unittest.TestCase):
    def test_open_palm(self):
        lm = build_landmarks(thumb="open")
        self.assertEqual(classify_landmarks(lm), Gesture.OPEN_PALM)
        self.assertEqual(count_extended_fingers(lm), 5)

    def test_fist(self):
        lm = build_landmarks(
            thumb="curled", index="curled", middle="curled", ring="curled", pinky="curled"
        )
        self.assertEqual(classify_landmarks(lm), Gesture.FIST)
        self.assertEqual(count_extended_fingers(lm), 0)

    def test_thumbs_up(self):
        lm = build_landmarks(
            thumb="up", index="curled", middle="curled", ring="curled", pinky="curled"
        )
        self.assertEqual(classify_landmarks(lm), Gesture.THUMBS_UP)

    def test_peace(self):
        lm = build_landmarks(
            thumb="curled", index="extended", middle="extended", ring="curled", pinky="curled"
        )
        self.assertEqual(classify_landmarks(lm), Gesture.PEACE)
        self.assertEqual(count_extended_fingers(lm), 2)

    def test_pointing(self):
        lm = build_landmarks(
            thumb="curled", index="extended", middle="curled", ring="curled", pinky="curled"
        )
        self.assertEqual(classify_landmarks(lm), Gesture.POINTING)
        self.assertEqual(count_extended_fingers(lm), 1)

    def test_ok(self):
        lm = build_landmarks(
            thumb="ok", index="ok", middle="extended", ring="extended", pinky="extended", ok=True
        )
        self.assertEqual(classify_landmarks(lm), Gesture.OK)

    def test_ily(self):
        lm = build_landmarks(
            thumb="up", index="extended", middle="curled", ring="curled", pinky="extended"
        )
        self.assertEqual(classify_landmarks(lm), Gesture.ILY)


if __name__ == "__main__":
    unittest.main()
