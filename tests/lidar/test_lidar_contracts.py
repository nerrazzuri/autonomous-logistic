from __future__ import annotations

import pytest


def test_can_create_valid_lidar_scan_point() -> None:
    from shared.lidar.contracts import LidarScanPoint

    point = LidarScanPoint(angle_rad=0.5, range_m=1.25, valid=True)

    assert point.angle_rad == 0.5
    assert point.range_m == 1.25
    assert point.valid is True


def test_invalid_point_uses_none_range() -> None:
    from shared.lidar.contracts import LidarScanPoint

    point = LidarScanPoint(angle_rad=1.0, range_m=None, valid=False)

    assert point.range_m is None
    assert point.valid is False


def test_valid_point_requires_float_range() -> None:
    from shared.lidar.contracts import LidarScanPoint

    with pytest.raises(ValueError, match="range_m"):
        LidarScanPoint(angle_rad=0.0, range_m=None, valid=True)


def test_invalid_point_rejects_non_none_range() -> None:
    from shared.lidar.contracts import LidarScanPoint

    with pytest.raises(ValueError, match="range_m"):
        LidarScanPoint(angle_rad=0.0, range_m=2.0, valid=False)


def test_can_create_valid_lidar_scan_frame() -> None:
    from shared.lidar.contracts import LidarScanFrame, LidarScanPoint

    frame = LidarScanFrame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=123.456,
        angle_min=-1.57,
        angle_max=1.57,
        angle_increment=0.01,
        range_min=0.05,
        range_max=30.0,
        points=(
            LidarScanPoint(angle_rad=-1.57, range_m=1.0, valid=True),
            LidarScanPoint(angle_rad=-1.56, range_m=None, valid=False),
        ),
    )

    assert frame.robot_id == "robot-01"
    assert frame.frame_id == "laser"
    assert frame.total_points == 2


def test_empty_robot_id_is_rejected() -> None:
    from shared.lidar.contracts import LidarScanFrame

    with pytest.raises(ValueError, match="robot_id"):
        LidarScanFrame(
            robot_id="",
            frame_id="laser",
            timestamp_sec=1.0,
            angle_min=0.0,
            angle_max=1.0,
            angle_increment=0.1,
            range_min=0.05,
            range_max=10.0,
            points=(),
        )


def test_empty_frame_id_is_rejected() -> None:
    from shared.lidar.contracts import LidarScanFrame

    with pytest.raises(ValueError, match="frame_id"):
        LidarScanFrame(
            robot_id="robot-01",
            frame_id="",
            timestamp_sec=1.0,
            angle_min=0.0,
            angle_max=1.0,
            angle_increment=0.1,
            range_min=0.05,
            range_max=10.0,
            points=(),
        )


def test_invalid_range_min_range_max_is_rejected() -> None:
    from shared.lidar.contracts import LidarScanFrame

    with pytest.raises(ValueError, match="range_max"):
        LidarScanFrame(
            robot_id="robot-01",
            frame_id="laser",
            timestamp_sec=1.0,
            angle_min=0.0,
            angle_max=1.0,
            angle_increment=0.1,
            range_min=1.0,
            range_max=1.0,
            points=(),
        )


def test_angle_increment_zero_is_rejected() -> None:
    from shared.lidar.contracts import LidarScanFrame

    with pytest.raises(ValueError, match="angle_increment"):
        LidarScanFrame(
            robot_id="robot-01",
            frame_id="laser",
            timestamp_sec=1.0,
            angle_min=0.0,
            angle_max=1.0,
            angle_increment=0.0,
            range_min=0.05,
            range_max=10.0,
            points=(),
        )


def test_total_valid_and_invalid_points_properties() -> None:
    from shared.lidar.contracts import LidarScanFrame, LidarScanPoint

    frame = LidarScanFrame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=-0.2,
        angle_max=0.2,
        angle_increment=0.2,
        range_min=0.05,
        range_max=10.0,
        points=(
            LidarScanPoint(angle_rad=-0.2, range_m=2.0, valid=True),
            LidarScanPoint(angle_rad=0.0, range_m=None, valid=False),
            LidarScanPoint(angle_rad=0.2, range_m=3.0, valid=True),
        ),
    )

    assert frame.total_points == 3
    assert frame.valid_points == 2
    assert frame.invalid_points == 1


def test_nearest_valid_range_returns_nearest_value() -> None:
    from shared.lidar.contracts import LidarScanFrame, LidarScanPoint

    frame = LidarScanFrame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=-0.3,
        angle_max=0.3,
        angle_increment=0.3,
        range_min=0.05,
        range_max=10.0,
        points=(
            LidarScanPoint(angle_rad=-0.3, range_m=4.0, valid=True),
            LidarScanPoint(angle_rad=0.0, range_m=None, valid=False),
            LidarScanPoint(angle_rad=0.3, range_m=1.5, valid=True),
        ),
    )

    assert frame.nearest_valid_range_m == 1.5


def test_nearest_valid_range_returns_none_when_no_valid_points_exist() -> None:
    from shared.lidar.contracts import LidarScanFrame, LidarScanPoint

    frame = LidarScanFrame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=-0.2,
        angle_max=0.2,
        angle_increment=0.2,
        range_min=0.05,
        range_max=10.0,
        points=(
            LidarScanPoint(angle_rad=-0.2, range_m=None, valid=False),
            LidarScanPoint(angle_rad=0.0, range_m=None, valid=False),
        ),
    )

    assert frame.nearest_valid_range_m is None
