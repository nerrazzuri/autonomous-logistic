from __future__ import annotations

"""Pure conversion helpers for LaserScan-like range sequences."""

import math
from collections.abc import Sequence

from shared.lidar.contracts import LidarScanFrame, LidarScanPoint


def convert_laser_scan_to_frame(
    *,
    robot_id: str,
    frame_id: str,
    timestamp_sec: float,
    angle_min: float,
    angle_max: float,
    angle_increment: float,
    range_min: float,
    range_max: float,
    ranges: Sequence[float],
) -> LidarScanFrame:
    points = tuple(
        _convert_range_to_point(
            angle_rad=angle_min + index * angle_increment,
            value=value,
            range_min=range_min,
            range_max=range_max,
        )
        for index, value in enumerate(ranges)
    )

    return LidarScanFrame(
        robot_id=robot_id,
        frame_id=frame_id,
        timestamp_sec=timestamp_sec,
        angle_min=angle_min,
        angle_max=angle_max,
        angle_increment=angle_increment,
        range_min=range_min,
        range_max=range_max,
        points=points,
    )


def _convert_range_to_point(
    *,
    angle_rad: float,
    value: float,
    range_min: float,
    range_max: float,
) -> LidarScanPoint:
    normalized = float(value)
    if (
        math.isnan(normalized)
        or not math.isfinite(normalized)
        or normalized < range_min
        or normalized > range_max
    ):
        return LidarScanPoint(angle_rad=angle_rad, range_m=None, valid=False)
    return LidarScanPoint(angle_rad=angle_rad, range_m=normalized, valid=True)


__all__ = [
    "convert_laser_scan_to_frame",
]
