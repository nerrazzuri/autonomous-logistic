from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _zip_text(bundle_path: Path, member: str) -> str:
    with zipfile.ZipFile(bundle_path) as archive:
        return archive.read(member).decode("utf-8")


def _zip_json(bundle_path: Path, member: str) -> object:
    return json.loads(_zip_text(bundle_path, member))


@pytest.fixture(autouse=True)
def reset_bundle_state(monkeypatch: pytest.MonkeyPatch):
    from shared.diagnostics import reset_diagnostic_store

    reset_diagnostic_store()
    yield
    reset_diagnostic_store()


def test_bundle_created_with_logs_and_generated_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from shared.diagnostics import get_diagnostic_store
    from shared.observability.diagnostic_bundle import DiagnosticBundleBuilder

    log_dir = tmp_path / "logs"
    output_dir = tmp_path / "diagnostics"
    _write(log_dir / "app.log", "Authorization: Bearer top-secret-token\nplain line\n")
    _write(
        log_dir / "app.jsonl",
        json.dumps(
            {
                "ts": "2026-01-01T00:00:00+00:00",
                "level": "ERROR",
                "module": "sdk_adapter",
                "event": "sdk.connect_failed",
                "message": "connect failed",
                "details": {"token": "top-secret-token"},
            }
        )
        + "\n",
    )
    _write(log_dir / "modules" / "sdk_adapter.jsonl", '{"event":"sdk.connect_failed","message":"connect failed"}\n')
    _write(log_dir / "ros" / "mapping.stdout.log", "password=super-secret\nstarted\n")
    _write(log_dir / "ros" / "mapping.stderr.log", "Bearer top-secret-token\n")
    _write(log_dir / ".env", "SUPERVISOR_TOKEN=should_not_be_included\n")
    _write(log_dir / "maps" / "facility_map.yaml", "image: should_not_be_included\n")

    get_diagnostic_store().create_event(
        severity="error",
        module="sdk_adapter",
        event="sdk.connect_failed",
        message="connect failed",
        details={"token": "top-secret-token", "visible": "ok"},
    )

    async def fake_status():
        return {
            "status": "degraded",
            "ts": "2026-01-01T00:00:00+00:00",
            "platform": {"app": "test", "uptime_seconds": 12.3, "version": None},
            "robots": {},
            "diagnostics": {"recent_count": 1, "error_count": 1, "critical_count": 0, "latest_error": None},
            "alerts": {"active_count": 0, "latest": None},
            "extensions": {},
        }

    monkeypatch.setattr("shared.observability.diagnostic_bundle.build_status_summary", fake_status)

    bundle_path = DiagnosticBundleBuilder(log_dir=log_dir, output_dir=output_dir, bundle_name="case-a").build()

    assert bundle_path.is_file()
    with zipfile.ZipFile(bundle_path) as archive:
        names = set(archive.namelist())

    assert "logs/app.log" in names
    assert "logs/app.jsonl" in names
    assert "logs/modules/sdk_adapter.jsonl" in names
    assert "logs/ros/mapping.stdout.log" in names
    assert "logs/ros/mapping.stderr.log" in names
    assert "generated/status_summary.json" in names
    assert "generated/recent_diagnostics.json" in names
    assert "generated/runtime_info.json" in names
    assert "generated/manifest.json" in names
    assert "generated/digest.md" in names
    assert ".env" not in "".join(names)
    assert "facility_map.yaml" not in "".join(names)

    assert "top-secret-token" not in _zip_text(bundle_path, "logs/app.log")
    assert "top-secret-token" not in _zip_text(bundle_path, "logs/app.jsonl")
    assert "super-secret" not in _zip_text(bundle_path, "logs/ros/mapping.stdout.log")

    diagnostics = _zip_json(bundle_path, "generated/recent_diagnostics.json")
    assert diagnostics[0]["details"]["token"] == "[REDACTED]"
    manifest = _zip_json(bundle_path, "generated/manifest.json")
    assert manifest["bundle_name"] == "case-a"
    assert manifest["files"]


def test_bundle_handles_missing_logs_and_records_truncation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from shared.observability.diagnostic_bundle import DiagnosticBundleBuilder

    log_dir = tmp_path / "logs"
    output_dir = tmp_path / "diagnostics"
    oversized = "token=very-secret-value\n" + ("x" * 512)
    _write(log_dir / "app.log", oversized)

    async def fake_status():
        return {
            "status": "ok",
            "ts": "2026-01-01T00:00:00+00:00",
            "platform": {"app": None, "uptime_seconds": 1.0, "version": None},
            "robots": {},
            "diagnostics": {"recent_count": 0, "error_count": 0, "critical_count": 0, "latest_error": None},
            "alerts": {"active_count": 0, "latest": None},
            "extensions": {},
        }

    monkeypatch.setattr("shared.observability.diagnostic_bundle.build_status_summary", fake_status)

    bundle_path = DiagnosticBundleBuilder(
        log_dir=log_dir,
        output_dir=output_dir,
        max_file_bytes=64,
        max_total_bytes=256,
        bundle_name="limited",
    ).build()

    manifest = _zip_json(bundle_path, "generated/manifest.json")
    entries = {entry["archive_path"]: entry for entry in manifest["files"]}
    assert entries["logs/app.log"]["truncated"] is True
    assert entries["generated/status_summary.json"]["included"] is True


def test_bundle_cli_creates_bundle_without_ros(tmp_path: Path) -> None:
    script = ROOT / "scripts" / "diagnostics" / "create_diagnostic_bundle.py"
    env = os.environ.copy()
    for key in ("PYTHONPATH", "ROS_DISTRO", "AMENT_PREFIX_PATH", "COLCON_PREFIX_PATH"):
        env.pop(key, None)

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--log-dir",
            str(tmp_path / "logs"),
            "--output-dir",
            str(tmp_path / "diagnostics"),
            "--name",
            "cli-bundle",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    bundle_path = Path(result.stdout.strip().splitlines()[-1])
    assert bundle_path.is_file()


def test_shared_bundle_code_has_no_apps_or_ros_or_app_terms() -> None:
    content = (ROOT / "shared" / "observability" / "diagnostic_bundle.py").read_text(encoding="utf-8")

    forbidden = (
        "from apps",
        "import apps",
        "import " + "rclpy",
        "from " + "rclpy",
        "LINE_A",
        "LINE_B",
        "LINE_C",
        "Sumitomo",
        "HUMAN_CONFIRMED_LOAD",
        "HUMAN_CONFIRMED_UNLOAD",
        "PATROL_",
        "patrol cycle",
        "patrol waypoint",
    )
    for marker in forbidden:
        assert marker not in content
