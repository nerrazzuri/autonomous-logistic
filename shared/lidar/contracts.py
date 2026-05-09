from __future__ import annotations

"""Platform-owned LiDAR scan data contracts."""

from dataclasses import dataclass
from typing import Iterable


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_non_negative_float(value: object, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be a float >= 0")
    normalized = float(value)
    if normalized < 0.0:
        raise ValueError(f"{field_name} must be a float >= 0")
    return normalized


@dataclass(frozen=True)
class LidarScanPoint:
    angle_rad: float
    range_m: float | None
    valid: bool

    def __post_init__(self) -> None:
        if not isinstance(self.angle_rad, (int, float)) or isinstance(self.angle_rad, bool):
            raise ValueError("angle_rad must be a float")
        object.__setattr__(self, "angle_rad", float(self.angle_rad))
        if not isinstance(self.valid, bool):
            raise ValueError("valid must be a bool")
        if self.valid:
            if not isinstance(self.range_m, (int, float)) or isinstance(self.range_m, bool):
                raise ValueError("range_m must be a float when valid is True")
            object.__setattr__(self, "range_m", float(self.range_m))
        elif self.range_m is not None:
            raise ValueError("range_m must be None when valid is False")


@dataclass(frozen=True)
class LidarScanFrame:
    robot_id: str
    frame_id: str
    timestamp_sec: float
    angle_min: float
    angle_max: float
    angle_increment: float
    range_min: float
    range_max: float
    points: tuple[LidarScanPoint, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "robot_id", _require_non_empty_string(self.robot_id, "robot_id"))
        object.__setattr__(self, "frame_id", _require_non_empty_string(self.frame_id, "frame_id"))
        object.__setattr__(self, "timestamp_sec", _require_non_negative_float(self.timestamp_sec, "timestamp_sec"))

        for field_name in ("angle_min", "angle_max", "angle_increment"):
            value = getattr(self, field_name)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"{field_name} must be a float")
            object.__setattr__(self, field_name, float(value))

        if self.angle_increment == 0.0:
            raise ValueError("angle_increment must not be 0")

        object.__setattr__(self, "range_min", _require_non_negative_float(self.range_min, "range_min"))
        object.__setattr__(self, "range_max", _require_non_negative_float(self.range_max, "range_max"))
        if self.range_max <= self.range_min:
            raise ValueError("range_max must be greater than range_min")

        normalized_points = self._normalize_points(self.points)
        object.__setattr__(self, "points", normalized_points)

    @staticmethod
    def _normalize_points(points: Iterable[LidarScanPoint]) -> tuple[LidarScanPoint, ...]:
        normalized = tuple(points)
        for point in normalized:
            if not isinstance(point, LidarScanPoint):
                raise ValueError("points must contain only LidarScanPoint instances")
        return normalized

    @property
    def total_points(self) -> int:
        return len(self.points)

    @property
    def valid_points(self) -> int:
        return sum(1 for point in self.points if point.valid)

    @property
    def invalid_points(self) -> int:
        return self.total_points - self.valid_points

    @property
    def nearest_valid_range_m(self) -> float | None:
        valid_ranges = [point.range_m for point in self.points if point.valid and point.range_m is not None]
        if not valid_ranges:
            return None
        return min(valid_ranges)


__all__ = [
    "LidarScanFrame",
    "LidarScanPoint",
]
