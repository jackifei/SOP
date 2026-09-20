"""Command-line entry point for the gesture app."""

from __future__ import annotations

import argparse
import json
import os
import sys

import cv2

from cam_hand.camera import Camera, list_cameras
from cam_hand.detector import Backend, HandDetector
from cam_hand.ui import GestureApp, render_frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cam-hand",
        description="USB camera hand gesture recognition app.",
    )
    parser.add_argument("--camera", type=int, default=0, help="USB camera index (default: 0)")
    parser.add_argument("--list-cameras", action="store_true", help="List available cameras and exit")
    parser.add_argument("--width", type=int, default=1280, help="Requested frame width")
    parser.add_argument("--height", type=int, default=720, help="Requested frame height")
    parser.add_argument(
        "--backend",
        choices=[item.value for item in Backend],
        default=Backend.AUTO.value,
        help="Detection backend (auto prefers MediaPipe)",
    )
    parser.add_argument("--no-mirror", action="store_true", help="Disable mirrored preview")
    parser.add_argument(
        "--min-detection-confidence",
        type=float,
        default=0.5,
        help="MediaPipe minimum detection confidence (0-1)",
    )
    parser.add_argument("--max-hands", type=int, default=1, help="Maximum hands tracked")
    parser.add_argument(
        "--snapshot",
        metavar="PATH",
        help="Capture one frame, save an annotated image, print the result, then exit",
    )
    return parser


def _make_detector(args: argparse.Namespace) -> HandDetector:
    return HandDetector(
        backend=args.backend,
        min_detection_confidence=args.min_detection_confidence,
        max_num_hands=args.max_hands,
    )


def _force_exit(code: int) -> None:
    """Exit without waiting for MediaPipe's native worker threads."""
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def _run_snapshot(args: argparse.Namespace, detector: HandDetector) -> int:
    camera = Camera(args.camera, args.width, args.height)
    camera.open()
    try:
        frame = camera.read()
    finally:
        camera.release()
    if not args.no_mirror:
        frame = cv2.flip(frame, 1)

    result = detector.detect(frame)
    annotated = render_frame(
        frame.copy(),
        result,
        fps=0.0,
        camera_index=args.camera,
        backend_name=detector.backend.value,
        show_help=False,
        detect_enabled=True,
        mirror=not args.no_mirror,
    )
    cv2.imwrite(args.snapshot, annotated)

    info = {
        "camera": args.camera,
        "backend": detector.backend.value,
        "gesture": result.label if result else None,
        "finger_count": int(result.finger_count) if result else 0,
        "snapshot": args.snapshot,
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_cameras:
        cameras = list_cameras()
        if not cameras:
            print("No cameras found.")
            return 1
        for camera in cameras:
            description = camera.description or "USB Camera"
            print(f"Camera {camera.index}: {description}")
        return 0

    detector = _make_detector(args)
    mediapipe_used = detector.backend == Backend.MEDIAPIPE
    result_code = 0
    try:
        if args.snapshot:
            result_code = _run_snapshot(args, detector)
        else:
            app = GestureApp(
                camera_index=args.camera,
                width=args.width,
                height=args.height,
                mirror=not args.no_mirror,
                detector=detector,
            )
            app.run()
    finally:
        detector.close()

    if mediapipe_used:
        _force_exit(result_code)
    return result_code

