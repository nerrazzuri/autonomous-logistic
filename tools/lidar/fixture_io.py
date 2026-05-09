from __future__ import annotations

"""Pure Python helpers for LiDAR scan fixture files."""

from collections.abc import Sequence
import json
import math
from pathlib import Path
from typing import Any


def save_scan_fixture(
    *,
    output: str | Path,
    robot_id: str,
    topic: str,
    frame_id: str,
    timestamp_sec: float,
    angle_min: float,
    angle_max: float,
    angle_increment: float,
    range_min: float,
    range_max: float,
    ranges: Sequence[float | None],
) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "source": "ros2_laserscan",
        "robot_id": robot_id,
        "topic": topic,
        "frame_id": frame_id,
        "timestamp_sec": float(timestamp_sec),
        "angle_min": float(angle_min),
        "angle_max": float(angle_max),
        "angle_increment": float(angle_increment),
        "range_min": float(range_min),
        "range_max": float(range_max),
        "ranges": [_normalize_range_value(value) for value in ranges],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load_scan_fixture(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("scan fixture must contain a top-level JSON object")
    return payload


def _normalize_range_value(value: float | None) -> float | None:
    if value is None:
        return None
    normalized = float(value)
    if math.isnan(normalized) or not math.isfinite(normalized):
        return None
    return normalized


__all__ = [
    "load_scan_fixture",
    "save_scan_fixture",
]
