# LiDAR Fixtures

This directory holds raw LaserScan-style JSON fixtures recorded from the real M10 UART LiDAR.

These fixtures are replay inputs, not ground-truth labels. Obstacle expectations below are based on the current obstacle detector settings from A5:

- front arc: `+/-45 deg`
- stop threshold: `0.8 m`

## Fixture Notes

- `empty_room.json`
  - Scenario: nominal empty capture in the available recording space.
  - Nearest front valid range: `0.6720000505447388 m`
  - Expected behavior at `0.8 m`: obstacle detected
  - Important: this is not a true clear fixture, because it contains a near-front return inside the current threshold.

- `wall_front.json`
  - Scenario: flat wall ahead.
  - Nearest front valid range: `0.8519999980926514 m`
  - Expected behavior at `0.8 m`: clear

- `object_50cm_front.json`
  - Scenario: compact object centered in front of the LiDAR.
  - Nearest front valid range: `0.5130000114440918 m`
  - Expected behavior at `0.8 m`: obstacle detected

- `object_left.json`
  - Scenario: compact object offset to the left of the front arc.
  - Nearest front valid range: `0.9699999690055847 m`
  - Expected behavior at `0.8 m`: clear

- `object_right.json`
  - Scenario: compact object offset to the right of the front arc.
  - Nearest front valid range: `0.9670000672340393 m`
  - Expected behavior at `0.8 m`: clear

## Re-record Recommendation

The current `empty_room.json` is useful as a historical real capture, but it should not be treated as a true-clear baseline. When a more open space is available, record a replacement such as `true_clear_room.json`.

To record a true clear fixture:

- Place the LiDAR at least `1.5 m` away from any object in the front `+/-45 deg` arc.
- Keep your body, laptop, cables, table legs, and wall outside the front arc.
- Run:

```bash
python3.10 -m tools.lidar.record_scan_fixture --output tests/fixtures/lidar/true_clear_room.json
```

Keep these files as raw scan data rather than derived obstacle labels or converted platform frames.
