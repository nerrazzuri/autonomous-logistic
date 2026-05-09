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


def test_log_digest_reads_structured_logs_and_handles_malformed_lines(tmp_path: Path) -> None:
    from shared.observability.log_digest import build_log_digest, render_log_digest_markdown

    log_dir = tmp_path / "logs"
    _write(
        log_dir / "app.jsonl",
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-01-01T00:00:00+00:00",
                        "level": "ERROR",
                        "module": "sdk_adapter",
                        "event": "sdk.connect_failed",
                        "message": "connect failed",
                        "error_code": "sdk.connect_failed",
                        "details": {"token": "secret-token"},
                    }
                ),
                "{not-json",
                json.dumps(
                    {
                        "ts": "2026-01-01T00:00:01+00:00",
                        "level": "INFO",
                        "module": "process_logs",
                        "event": "process.started",
                        "message": "Process started.",
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-01-01T00:00:02+00:00",
                        "level": "ERROR",
                        "module": "process_logs",
                        "event": "process.failed",
                        "message": "Process exited with a non-zero code.",
                        "error_code": "process.exited_nonzero",
                        "details": {"exit_code": 2},
                    }
                ),
            ]
        )
        + "\n",
    )

    summary = build_log_digest(log_dir=log_dir)
    markdown = render_log_digest_markdown(summary)

    assert summary["overall"]["total_structured_events"] == 3
    assert summary["overall"]["malformed_lines"] == 1
    assert summary["overall"]["levels"]["ERROR"] == 2
    assert summary["overall"]["modules"]["sdk_adapter"] == 1
    assert summary["overall"]["error_codes"]["sdk.connect_failed"] == 1
    assert summary["process"]["started"] == 1
    assert summary["process"]["failed"] == 1
    assert summary["process"]["nonzero_exits"] == 1
    assert summary["latest_errors"][0]["details"]["token"] == "[REDACTED]"
    assert "secret-token" not in markdown
    assert "sdk_adapter" in markdown


def test_log_digest_reads_bundle_zip_and_output_file(tmp_path: Path) -> None:
    from shared.observability.log_digest import build_log_digest

    bundle_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(bundle_path, "w") as archive:
        archive.writestr(
            "logs/app.jsonl",
            json.dumps(
                {
                    "ts": "2026-01-01T00:00:00+00:00",
                    "level": "CRITICAL",
                    "module": "navigation",
                    "event": "navigation.failed",
                    "message": "navigation failed",
                    "error_code": "navigation.failed",
                }
            )
            + "\n",
        )
        archive.writestr(
            "generated/status_summary.json",
            json.dumps(
                {
                    "status": "error",
                    "diagnostics": {"error_count": 3},
                    "alerts": {"active_count": 1},
                }
            ),
        )
        archive.writestr(
            "generated/manifest.json",
            json.dumps(
                {
                    "files": [
                        {
                            "archive_path": "logs/app.jsonl",
                            "included": True,
                            "truncated": False,
                        }
                    ]
                }
            ),
        )

    summary = build_log_digest(bundle_path=bundle_path)

    assert summary["overall"]["total_structured_events"] == 1
    assert summary["status_summary"]["status"] == "error"
    assert summary["status_summary"]["diagnostics_error_count"] == 3
    assert summary["status_summary"]["alert_count"] == 1


def test_log_digest_cli_prints_markdown_and_writes_output(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    output = tmp_path / "digest.md"
    script = ROOT / "scripts" / "diagnostics" / "log_digest.py"
    _write(
        log_dir / "app.jsonl",
        json.dumps(
            {
                "ts": "2026-01-01T00:00:00+00:00",
                "level": "INFO",
                "module": "sdk_adapter",
                "event": "sdk.connected",
                "message": "connected",
            }
        )
        + "\n",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--log-dir",
            str(log_dir),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "Log Digest" in result.stdout
    assert output.is_file()
    assert "sdk_adapter" in output.read_text(encoding="utf-8")


def test_log_digest_handles_missing_logs_without_crashing(tmp_path: Path) -> None:
    from shared.observability.log_digest import build_log_digest

    summary = build_log_digest(log_dir=tmp_path / "missing")

    assert summary["overall"]["total_structured_events"] == 0
    assert summary["warnings"]


def test_shared_log_digest_code_has_no_apps_or_ros_or_app_terms() -> None:
    content = (ROOT / "shared" / "observability" / "log_digest.py").read_text(encoding="utf-8")

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
