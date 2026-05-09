from __future__ import annotations

import math
from pathlib import Path


def test_save_and_load_fixture_round_trip(tmp_path: Path) -> None:
    from tools.lidar.fixture_io import load_scan_fixture, save_scan_fixture

    output = tmp_path / "scan_fixture.json"
    save_scan_fixture(
        output=output,
        robot_id="workstation_test",
        topic="/scan",
        frame_id="laser",
        timestamp_sec=1778314490.31,
        angle_min=-3.14,
        angle_max=3.14,
        angle_increment=0.1,
        range_min=0.15,
        range_max=50.0,
        ranges=(0.33, 0.34, None, 0.55),
    )

    fixture = load_scan_fixture(output)

    assert fixture["schema_version"] == 1
    assert fixture["source"] == "".join(("ros", "2", "_laserscan"))
    assert fixture["robot_id"] == "workstation_test"
    assert fixture["topic"] == "/scan"
    assert fixture["frame_id"] == "laser"
    assert fixture["timestamp_sec"] == 1778314490.31
    assert fixture["ranges"] == [0.33, 0.34, None, 0.55]


def test_nan_and_infinity_are_serialized_as_null(tmp_path: Path) -> None:
    from tools.lidar.fixture_io import load_scan_fixture, save_scan_fixture

    output = tmp_path / "scan_fixture.json"
    save_scan_fixture(
        output=output,
        robot_id="workstation_test",
        topic="/scan",
        frame_id="laser",
        timestamp_sec=10.0,
        angle_min=0.0,
        angle_max=0.3,
        angle_increment=0.1,
        range_min=0.15,
        range_max=50.0,
        ranges=(math.nan, math.inf, -math.inf, 1.25),
    )

    fixture = load_scan_fixture(output)

    assert fixture["ranges"] == [None, None, None, 1.25]


def test_fixture_can_be_loaded_and_converted_to_lidar_frame(tmp_path: Path) -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame
    from tools.lidar.fixture_io import load_scan_fixture, save_scan_fixture

    output = tmp_path / "scan_fixture.json"
    save_scan_fixture(
        output=output,
        robot_id="workstation_test",
        topic="/scan",
        frame_id="laser",
        timestamp_sec=20.5,
        angle_min=-0.2,
        angle_max=0.2,
        angle_increment=0.2,
        range_min=0.15,
        range_max=50.0,
        ranges=(0.33, None, 0.55),
    )

    fixture = load_scan_fixture(output)
    converter_ranges = tuple(math.nan if value is None else float(value) for value in fixture["ranges"])
    frame = convert_laser_scan_to_frame(
        robot_id=fixture["robot_id"],
        frame_id=fixture["frame_id"],
        timestamp_sec=float(fixture["timestamp_sec"]),
        angle_min=float(fixture["angle_min"]),
        angle_max=float(fixture["angle_max"]),
        angle_increment=float(fixture["angle_increment"]),
        range_min=float(fixture["range_min"]),
        range_max=float(fixture["range_max"]),
        ranges=converter_ranges,
    )

    assert frame.robot_id == "workstation_test"
    assert frame.frame_id == "laser"
    assert frame.timestamp_sec == 20.5
    assert frame.total_points == 3
    assert frame.valid_points == 2
    assert frame.invalid_points == 1
