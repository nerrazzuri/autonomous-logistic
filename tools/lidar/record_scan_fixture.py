from __future__ import annotations

"""Record one ROS2 LaserScan message into a reusable JSON fixture."""

import argparse
from pathlib import Path
import sys
import time

from tools.lidar.fixture_io import save_scan_fixture


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record one /scan message into a JSON fixture.")
    parser.add_argument("--topic", default="/scan", help="ROS2 LaserScan topic to subscribe to.")
    parser.add_argument("--robot-id", default="workstation_test", help="Robot ID to embed in the fixture.")
    parser.add_argument(
        "--output",
        default="tests/fixtures/lidar/scan_fixture.json",
        help="Output JSON fixture path.",
    )
    parser.add_argument("--timeout-sec", type=float, default=10.0, help="Seconds to wait for one scan message.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        scan_message = _record_single_scan(topic=args.topic, timeout_sec=args.timeout_sec)
    except TimeoutError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ImportError as exc:
        print(f"ROS2 dependencies unavailable: {exc}", file=sys.stderr)
        return 2

    output_path = save_scan_fixture(
        output=args.output,
        robot_id=args.robot_id,
        topic=args.topic,
        frame_id=scan_message.header.frame_id,
        timestamp_sec=_stamp_to_seconds(scan_message.header.stamp),
        angle_min=scan_message.angle_min,
        angle_max=scan_message.angle_max,
        angle_increment=scan_message.angle_increment,
        range_min=scan_message.range_min,
        range_max=scan_message.range_max,
        ranges=tuple(scan_message.ranges),
    )
    print(f"Saved fixture: {output_path}")
    return 0


def _record_single_scan(*, topic: str, timeout_sec: float):
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import LaserScan

    class ScanRecorder(Node):
        def __init__(self, scan_topic: str) -> None:
            super().__init__("scan_fixture_recorder")
            self.scan_message: LaserScan | None = None
            self.subscription = self.create_subscription(LaserScan, scan_topic, self._callback, 10)

        def _callback(self, message: LaserScan) -> None:
            if self.scan_message is None:
                self.scan_message = message

    rclpy.init()
    node = ScanRecorder(topic)
    deadline = time.monotonic() + timeout_sec
    try:
        while rclpy.ok() and node.scan_message is None and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        if node.scan_message is None:
            raise TimeoutError(f"Timed out after {timeout_sec} seconds waiting for a LaserScan on {topic}")
        return node.scan_message
    finally:
        node.destroy_node()
        rclpy.shutdown()


def _stamp_to_seconds(stamp: object) -> float:
    sec = getattr(stamp, "sec", 0)
    nanosec = getattr(stamp, "nanosec", 0)
    return float(sec) + float(nanosec) / 1_000_000_000.0


if __name__ == "__main__":
    raise SystemExit(main())
