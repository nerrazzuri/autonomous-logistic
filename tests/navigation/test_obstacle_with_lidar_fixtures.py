from __future__ import annotations

import math
from pathlib import Path

import pytest

from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame
from tools.lidar.fixture_io import load_scan_fixture


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "lidar"
CURRENT_STOP_DISTANCE_M = 0.8
CURRENT_FRONT_ARC_HALF_DEG = 45.0


def _load_frame(name: str):
    fixture = load_scan_fixture(FIXTURE_DIR / name)
    ranges = tuple(math.nan if value is None else float(value) for value in fixture["ranges"])
    return convert_laser_scan_to_frame(
        robot_id=fixture["robot_id"],
        frame_id=fixture["frame_id"],
        timestamp_sec=float(fixture["timestamp_sec"]),
        angle_min=float(fixture["angle_min"]),
        angle_max=float(fixture["angle_max"]),
        angle_increment=float(fixture["angle_increment"]),
        range_min=float(fixture["range_min"]),
        range_max=float(fixture["range_max"]),
        ranges=ranges,
    )


def _nearest_front_range(frame, arc_half_deg: float = 45.0):
    arc_half_rad = math.radians(arc_half_deg)
    values = [
        point.range_m
        for point in frame.points
        if point.valid and point.range_m is not None and abs(point.angle_rad) <= arc_half_rad
    ]
    return min(values) if values else None


def _front_measurement(name: str, stop_distance_m: float = CURRENT_STOP_DISTANCE_M, arc_half_deg: float = CURRENT_FRONT_ARC_HALF_DEG):
    from shared.navigation.obstacle import _check_forward_arc_frame

    frame = _load_frame(name)
    nearest_front = _nearest_front_range(frame, arc_half_deg=arc_half_deg)
    blocked = _check_forward_arc_frame(frame, stop_distance_m=stop_distance_m, arc_half_deg=arc_half_deg)
    return frame, nearest_front, blocked


def test_object_50cm_front_fixture_triggers_front_obstacle() -> None:
    _, nearest_front, blocked = _front_measurement("object_50cm_front.json")

    assert nearest_front == pytest.approx(0.5130000114440918)
    assert blocked is True


def test_empty_room_fixture_matches_recorded_front_distance() -> None:
    _, nearest_front, blocked = _front_measurement("empty_room.json")

    assert nearest_front == pytest.approx(0.6720000505447388)
    assert blocked is True


def test_object_left_fixture_stays_outside_current_front_threshold() -> None:
    _, nearest_front, blocked = _front_measurement("object_left.json")

    assert nearest_front == pytest.approx(0.9699999690055847)
    assert blocked is False


def test_object_right_fixture_stays_outside_current_front_threshold() -> None:
    _, nearest_front, blocked = _front_measurement("object_right.json")

    assert nearest_front == pytest.approx(0.9670000672340393)
    assert blocked is False


def test_wall_front_fixture_matches_recorded_threshold_result() -> None:
    _, nearest_front, blocked = _front_measurement("wall_front.json")

    assert nearest_front == pytest.approx(0.8519999980926514)
    assert blocked is False
