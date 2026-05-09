## M10 UART Workstation Baseline

This runbook captures the completed workstation-side M10 UART LiDAR baseline and the handoff prep for the next quadruped deployment stage.

## Confirmed Baseline

Current confirmed workstation status:

- M10 UART LiDAR bring-up is working on the workstation.
- Stable device alias: `/dev/lslidar`.
- ROS topic: `/scan`.
- Message type: `sensor_msgs/msg/LaserScan`.
- Observed publish rate: about `10 Hz`.
- Observed `frame_id`: `laser`.

## Workstation Bring-Up

Source ROS2 and the Wheeltec overlay:

```bash
source /opt/ros/humble/setup.bash
source ~/Projects/wheeltec_ros2/install/setup.bash
```

Start the LiDAR driver:

```bash
ros2 launch lslidar_driver lsm10_uart_launch.py
```

Verify the topic rate and one sample message:

```bash
ros2 topic hz /scan
ros2 topic echo /scan --once
```

Expected baseline:

- `/scan` is live.
- The topic rate is stable near `10 Hz`.
- The sample message reports `frame_id` as `laser`.

## Autonomous Platform Verification

Run the current LiDAR and obstacle validation suite:

```bash
rtk python3.10 -m pytest -q tests/lidar tests/navigation tests/test_obstacle_detector.py tests/test_obstacle.py tests/test_runtime_startup.py tests/test_navigator.py
```

This validates:

- platform-owned LiDAR contracts
- raw LaserScan-like conversion
- fixture load/replay behavior
- obstacle detection using `LidarScanFrame`
- preserved stop-and-wait obstacle behavior
- startup and navigator compatibility

## Fixture Recording

To record a new clear-baseline fixture:

```bash
python3.10 -m tools.lidar.record_scan_fixture --output tests/fixtures/lidar/true_clear_room.json
```

Recommended setup for a true-clear recording:

- keep all objects at least `1.5 m` away in the front `+/-45 deg` arc
- keep your body, laptop, cables, table legs, and walls outside the front arc

## Current Fixture Interpretation

These interpretations reflect the current obstacle detector threshold of `0.8 m` and the current front arc of `+/-45 deg`.

- `empty_room.json`
  - obstacle detected
  - nearest front valid range is about `0.6720000505447388 m`
  - this is not a true-clear fixture
- `wall_front.json`
  - clear
  - nearest front valid range is about `0.8519999980926514 m`
- `object_50cm_front.json`
  - obstacle detected
  - nearest front valid range is about `0.5130000114440918 m`
- `object_left.json`
  - clear
  - nearest front valid range is about `0.9699999690055847 m`
- `object_right.json`
  - clear
  - nearest front valid range is about `0.9670000672340393 m`

## Architecture Summary

Current workstation-side data flow:

```text
ROS2 /scan
  -> LaserScan-like raw fields
  -> convert_laser_scan_to_frame
  -> LidarScanFrame
  -> shared/navigation/obstacle.py
  -> OBSTACLE_DETECTED / OBSTACLE_CLEARED
  -> navigator stop-and-wait
```

This is intentionally still a stop-and-wait safety path. It is not an avoidance stack.

## Intentionally Not Added

The current baseline intentionally does not include:

- multi-sector evaluator
- safety state generator
- dynamic avoidance
- standalone LiDAR API or dashboard
- standalone LiDAR app

## B-Stage Handoff Checklist

When the quadruped is available, the next stage should proceed in this order:

1. Mount the LiDAR on the quadruped.
2. Verify the device appears as `/dev/ttyUSB*` or `/dev/ttyACM*`.
3. Create a stable `/dev/lslidar` alias on the quadruped.
4. Build `lslidar_driver` on the quadruped.
5. Verify `/scan` locally on the quadruped.
6. Configure DDS discovery or a fallback bridge path.
7. Make the workstation see the quadruped `/scan`.
8. Wire `bridge_node` `/scan` input through `LidarScanFrame` into `obstacle.py`.
9. Add the static TF from `base_link` to `laser`.
10. Only then test SLAM.
11. Only then test end-to-end stop-and-wait movement.

## Notes

- Do not change obstacle thresholds during this handoff unless there is a separate validation task.
- Do not test movement until scan delivery, TF, and obstacle gating are all verified first.
