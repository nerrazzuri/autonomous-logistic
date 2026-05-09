from __future__ import annotations

import math

import pytest


def test_converts_normal_ranges_into_valid_points() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=12.5,
        angle_min=0.0,
        angle_max=0.2,
        angle_increment=0.1,
        range_min=0.05,
        range_max=10.0,
        ranges=(1.0, 2.0, 3.0),
    )

    assert tuple(point.valid for point in frame.points) == (True, True, True)
    assert tuple(point.range_m for point in frame.points) == (1.0, 2.0, 3.0)


def test_converts_nan_to_invalid_point() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=0.0,
        angle_max=0.0,
        angle_increment=0.1,
        range_min=0.05,
        range_max=10.0,
        ranges=(math.nan,),
    )

    assert frame.points[0].valid is False
    assert frame.points[0].range_m is None


def test_converts_positive_infinity_to_invalid_point() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=0.0,
        angle_max=0.0,
        angle_increment=0.1,
        range_min=0.05,
        range_max=10.0,
        ranges=(math.inf,),
    )

    assert frame.points[0].valid is False
    assert frame.points[0].range_m is None


def test_converts_negative_infinity_to_invalid_point() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=0.0,
        angle_max=0.0,
        angle_increment=0.1,
        range_min=0.05,
        range_max=10.0,
        ranges=(-math.inf,),
    )

    assert frame.points[0].valid is False
    assert frame.points[0].range_m is None


def test_converts_value_below_range_min_to_invalid_point() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=0.0,
        angle_max=0.0,
        angle_increment=0.1,
        range_min=0.5,
        range_max=10.0,
        ranges=(0.25,),
    )

    assert frame.points[0].valid is False
    assert frame.points[0].range_m is None


def test_converts_value_above_range_max_to_invalid_point() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=0.0,
        angle_max=0.0,
        angle_increment=0.1,
        range_min=0.05,
        range_max=5.0,
        ranges=(6.0,),
    )

    assert frame.points[0].valid is False
    assert frame.points[0].range_m is None


def test_computes_angles_correctly_for_multiple_points() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=3.0,
        angle_min=-0.2,
        angle_max=0.2,
        angle_increment=0.2,
        range_min=0.05,
        range_max=10.0,
        ranges=(1.0, 1.5, 2.0),
    )

    assert tuple(point.angle_rad for point in frame.points) == (-0.2, 0.0, 0.2)


def test_preserves_all_frame_metadata() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-02",
        frame_id="laser_frame",
        timestamp_sec=42.25,
        angle_min=-1.5,
        angle_max=1.5,
        angle_increment=0.05,
        range_min=0.12,
        range_max=25.0,
        ranges=(1.0,),
    )

    assert frame.robot_id == "robot-02"
    assert frame.frame_id == "laser_frame"
    assert frame.timestamp_sec == 42.25
    assert frame.angle_min == -1.5
    assert frame.angle_max == 1.5
    assert frame.angle_increment == 0.05
    assert frame.range_min == 0.12
    assert frame.range_max == 25.0


def test_returns_tuple_points_not_list() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=0.0,
        angle_max=0.1,
        angle_increment=0.1,
        range_min=0.05,
        range_max=10.0,
        ranges=(1.0, 2.0),
    )

    assert isinstance(frame.points, tuple)


def test_empty_ranges_creates_valid_frame_with_zero_points() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    frame = convert_laser_scan_to_frame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=0.0,
        angle_max=0.0,
        angle_increment=0.1,
        range_min=0.05,
        range_max=10.0,
        ranges=(),
    )

    assert frame.total_points == 0
    assert frame.points == ()


def test_invalid_contract_metadata_is_rejected() -> None:
    from shared.lidar.laser_scan_converter import convert_laser_scan_to_frame

    with pytest.raises(ValueError, match="robot_id"):
        convert_laser_scan_to_frame(
            robot_id="",
            frame_id="laser",
            timestamp_sec=1.0,
            angle_min=0.0,
            angle_max=0.0,
            angle_increment=0.1,
            range_min=0.05,
            range_max=10.0,
            ranges=(),
        )

    with pytest.raises(ValueError, match="frame_id"):
        convert_laser_scan_to_frame(
            robot_id="robot-01",
            frame_id="",
            timestamp_sec=1.0,
            angle_min=0.0,
            angle_max=0.0,
            angle_increment=0.1,
            range_min=0.05,
            range_max=10.0,
            ranges=(),
        )

    with pytest.raises(ValueError, match="range_max"):
        convert_laser_scan_to_frame(
            robot_id="robot-01",
            frame_id="laser",
            timestamp_sec=1.0,
            angle_min=0.0,
            angle_max=0.0,
            angle_increment=0.1,
            range_min=1.0,
            range_max=1.0,
            ranges=(),
        )
