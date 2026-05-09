# LiDAR Fixture Recording

This tooling records one real ROS2 `LaserScan` message into a reusable JSON fixture file. The saved fixture keeps raw scan metadata and range samples so later tests can replay the same scan without physical LiDAR hardware.

## Before Recording

Start the LiDAR driver first:

```bash
ros2 launch lslidar_driver lsm10_uart_launch.py
```

Verify the topic is live:

```bash
ros2 topic hz /scan
```

## Record One Fixture

```bash
source /opt/ros/humble/setup.bash
source ~/Projects/wheeltec_ros2/install/setup.bash
python3.10 -m tools.lidar.record_scan_fixture \
  --topic /scan \
  --robot-id workstation_test \
  --output tests/fixtures/lidar/object_50cm_front.json \
  --timeout-sec 10
```

Defaults:

- `--topic /scan`
- `--robot-id workstation_test`
- `--output tests/fixtures/lidar/scan_fixture.json`
- `--timeout-sec 10`

## Recommended Real-World Fixtures

- `empty_room.json`
  Nominal empty capture. In the current recorded sample, a near-front return still lands inside the obstacle threshold, so this is not a true clear fixture.
- `wall_front.json`
  Place the LiDAR facing a flat wall directly ahead.
- `object_50cm_front.json`
  Place a compact object centered about 50 cm in front of the LiDAR.
- `object_left.json`
  Place the object at a similar distance, but offset to the left side.
- `object_right.json`
  Place the object at a similar distance, but offset to the right side.

Try to keep the LiDAR still during each capture and record one clean scene per file.

## Record a True Clear Fixture

If you need a genuine clear-baseline replay sample, record a separate fixture instead of overwriting `empty_room.json`.

- Place the LiDAR at least `1.5 m` away from any object in the front `+/-45 deg` arc.
- Keep your body, laptop, cables, table legs, and wall outside the front arc.
- Run:

```bash
python3.10 -m tools.lidar.record_scan_fixture --output tests/fixtures/lidar/true_clear_room.json
```
