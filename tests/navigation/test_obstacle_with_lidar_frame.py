from __future__ import annotations

import math

from shared.lidar.contracts import LidarScanFrame, LidarScanPoint


def _frame(points: tuple[LidarScanPoint, ...]) -> LidarScanFrame:
    return LidarScanFrame(
        robot_id="robot-01",
        frame_id="laser",
        timestamp_sec=1.0,
        angle_min=-math.pi / 2,
        angle_max=math.pi / 2,
        angle_increment=math.pi / 180,
        range_min=0.15,
        range_max=50.0,
        points=points,
    )


def test_lidar_frame_with_front_obstacle_triggers_detection() -> None:
    from shared.navigation.obstacle import _check_forward_arc_frame

    frame = _frame(
        (
            LidarScanPoint(angle_rad=0.0, range_m=0.5, valid=True),
            LidarScanPoint(angle_rad=1.2, range_m=2.0, valid=True),
        )
    )

    assert _check_forward_arc_frame(frame, stop_distance_m=0.8, arc_half_deg=45.0) is True


def test_lidar_frame_with_clear_values_is_clear() -> None:
    from shared.navigation.obstacle import _check_forward_arc_frame

    frame = _frame(
        (
            LidarScanPoint(angle_rad=-0.1, range_m=1.2, valid=True),
            LidarScanPoint(angle_rad=0.1, range_m=1.3, valid=True),
        )
    )

    assert _check_forward_arc_frame(frame, stop_distance_m=0.8, arc_half_deg=45.0) is False


def test_invalid_points_are_ignored() -> None:
    from shared.navigation.obstacle import _check_forward_arc_frame

    frame = _frame(
        (
            LidarScanPoint(angle_rad=0.0, range_m=None, valid=False),
            LidarScanPoint(angle_rad=0.2, range_m=1.1, valid=True),
        )
    )

    assert _check_forward_arc_frame(frame, stop_distance_m=0.8, arc_half_deg=45.0) is False


def test_obstacle_outside_front_arc_does_not_trigger() -> None:
    from shared.navigation.obstacle import _check_forward_arc_frame

    frame = _frame(
        (
            LidarScanPoint(angle_rad=math.radians(60.0), range_m=0.4, valid=True),
        )
    )

    assert _check_forward_arc_frame(frame, stop_distance_m=0.8, arc_half_deg=45.0) is False


def test_empty_frame_is_clear() -> None:
    from shared.navigation.obstacle import _check_forward_arc_frame

    frame = _frame(())

    assert _check_forward_arc_frame(frame, stop_distance_m=0.8, arc_half_deg=45.0) is False
