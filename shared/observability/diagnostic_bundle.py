"""Safe diagnostic bundle generation for logs, summaries, and recent diagnostics."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
from typing import Any
import zipfile

from shared.core.logger import get_logger
from shared.diagnostics import DiagnosticReporter, get_diagnostic_reporter, get_diagnostic_store
from shared.diagnostics.redaction import REDACTION_MARKER, SENSITIVE_KEYWORDS, redact_mapping
from shared.observability.alerts import get_alert_router
from shared.observability.log_digest import build_log_digest, render_log_digest_markdown
from shared.observability.status import build_status_summary


logger = get_logger(__name__)

DEFAULT_MAX_FILE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_TOTAL_BYTES = 25 * 1024 * 1024


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    return repr(value)


def _redact_text(text: str) -> str:
    redacted = text
    redacted = re.sub(r"(?i)bearer\s+[A-Za-z0-9._=-]+", REDACTION_MARKER, redacted)
    for keyword in SENSITIVE_KEYWORDS:
        redacted = re.sub(
            rf"(?i)\b([A-Za-z0-9_.-]*{re.escape(keyword)}[A-Za-z0-9_.-]*)\b\s*[:=]\s*([^\s,;]+)",
            rf"\1={REDACTION_MARKER}",
            redacted,
        )
    return redacted


def _sanitize_log_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            lines.append(_redact_text(line))
            continue
        if isinstance(parsed, Mapping):
            lines.append(json.dumps(_safe_json(redact_mapping(parsed)), sort_keys=True))
        else:
            lines.append(_redact_text(line))
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def _run_async(value: Any) -> Any:
    if not asyncio.iscoroutine(value):
        return value
    return asyncio.run(value)


@dataclass
class _ManifestEntry:
    original_path: str
    archive_path: str
    included: bool
    bytes_written: int
    truncated: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_path": self.original_path,
            "archive_path": self.archive_path,
            "included": self.included,
            "bytes_written": self.bytes_written,
            "truncated": self.truncated,
            "reason": self.reason,
        }


class DiagnosticBundleBuilder:
    def __init__(
        self,
        *,
        log_dir: str | Path = "logs",
        output_dir: str | Path = "diagnostics",
        bundle_name: str | None = None,
        include_status_summary: bool = True,
        include_recent_diagnostics: bool = True,
        include_alerts: bool = True,
        include_runtime_info: bool = True,
        include_digest: bool = True,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
        now: Callable[[], datetime] | None = None,
        reporter: DiagnosticReporter | None = None,
        raise_on_error: bool = False,
    ) -> None:
        self.log_dir = Path(log_dir)
        self.output_dir = Path(output_dir)
        self.bundle_name = bundle_name
        self.include_status_summary = include_status_summary
        self.include_recent_diagnostics = include_recent_diagnostics
        self.include_alerts = include_alerts
        self.include_runtime_info = include_runtime_info
        self.include_digest = include_digest
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.now = now or _utc_now
        self.reporter = reporter
        self.raise_on_error = raise_on_error
        if self.max_file_bytes <= 0:
            raise ValueError("max_file_bytes must be positive")
        if self.max_total_bytes <= 0:
            raise ValueError("max_total_bytes must be positive")

    def build(self) -> Path:
        try:
            return self._build()
        except Exception:
            self._report(
                "error",
                event="diagnostic_bundle.failed",
                message="Diagnostic bundle generation failed.",
            )
            if self.raise_on_error:
                raise
            raise

    def _build(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        created_at = self.now()
        bundle_name = self.bundle_name or f"diagnostic_bundle_{created_at.strftime('%Y%m%d_%H%M%S')}"
        bundle_path = self.output_dir / f"{bundle_name}.zip"
        manifest_entries: list[_ManifestEntry] = []
        total_written = 0

        with tempfile.TemporaryDirectory(prefix="diagnostic_bundle_") as temp_dir_str:
            staging = Path(temp_dir_str)

            def stage_text(
                original_path: str,
                archive_path: str,
                text: str,
                *,
                enforce_limit: bool = True,
                allow_truncate: bool = True,
            ) -> None:
                nonlocal total_written
                encoded = text.encode("utf-8")
                truncated = False
                if allow_truncate and len(encoded) > self.max_file_bytes:
                    notice = "\n[TRUNCATED]\n".encode("utf-8")
                    encoded = encoded[: max(0, self.max_file_bytes - len(notice))] + notice
                    truncated = True
                if enforce_limit and total_written + len(encoded) > self.max_total_bytes:
                    manifest_entries.append(
                        _ManifestEntry(original_path, archive_path, False, 0, False, "max_total_bytes_exceeded")
                    )
                    return
                target = staging / archive_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(encoded)
                total_written += len(encoded)
                manifest_entries.append(
                    _ManifestEntry(original_path, archive_path, True, len(encoded), truncated, None)
                )

            for path in self._collect_log_files():
                relative = path.relative_to(self.log_dir)
                archive_path = str(Path("logs") / relative)
                stage_text(str(path), archive_path, _sanitize_log_text(path.read_text(encoding="utf-8", errors="replace")))

            if self.include_status_summary:
                status_summary = _safe_json(redact_mapping(_run_async(build_status_summary())))
                stage_text(
                    "generated:status_summary",
                    "generated/status_summary.json",
                    json.dumps(status_summary, indent=2, sort_keys=True),
                    enforce_limit=False,
                    allow_truncate=False,
                )

            if self.include_recent_diagnostics:
                diagnostics = _safe_json(get_diagnostic_store().to_list(limit=200))
                stage_text(
                    "generated:recent_diagnostics",
                    "generated/recent_diagnostics.json",
                    json.dumps(diagnostics, indent=2, sort_keys=True),
                    enforce_limit=False,
                    allow_truncate=False,
                )

            if self.include_alerts:
                try:
                    alerts = [_safe_json(alert.to_dict()) for alert in get_alert_router().list_alerts(limit=200)]
                except Exception:
                    alerts = []
                stage_text(
                    "generated:recent_alerts",
                    "generated/recent_alerts.json",
                    json.dumps(alerts, indent=2, sort_keys=True),
                    enforce_limit=False,
                    allow_truncate=False,
                )

            if self.include_runtime_info:
                runtime_info = {
                    "generated_at": created_at.isoformat(),
                    "python_version": sys.version,
                    "platform": platform.platform(),
                    "cwd": os.getcwd(),
                    "log_dir": str(self.log_dir),
                    "output_dir": str(self.output_dir),
                }
                stage_text(
                    "generated:runtime_info",
                    "generated/runtime_info.json",
                    json.dumps(runtime_info, indent=2, sort_keys=True),
                    enforce_limit=False,
                    allow_truncate=False,
                )

            if self.include_digest:
                digest = build_log_digest(log_dir=self.log_dir)
                stage_text(
                    "generated:digest",
                    "generated/digest.md",
                    render_log_digest_markdown(digest),
                    enforce_limit=False,
                    allow_truncate=False,
                )

            manifest = {
                "bundle_name": bundle_name,
                "created_at": created_at.isoformat(),
                "max_file_bytes": self.max_file_bytes,
                "max_total_bytes": self.max_total_bytes,
                "files": [entry.to_dict() for entry in manifest_entries],
            }
            stage_text(
                "generated:manifest",
                "generated/manifest.json",
                json.dumps(manifest, indent=2, sort_keys=True),
                enforce_limit=False,
                allow_truncate=False,
            )

            with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file_path in staging.rglob("*"):
                    if file_path.is_file():
                        archive.write(file_path, file_path.relative_to(staging))

        self._report(
            "info",
            event="diagnostic_bundle.created",
            message="Diagnostic bundle created.",
            details={"bundle_path": str(bundle_path), "bundle_name": bundle_name},
        )
        return bundle_path

    def _collect_log_files(self) -> list[Path]:
        candidates: list[Path] = []
        for name in ("app.log", "app.jsonl"):
            path = self.log_dir / name
            if path.is_file():
                candidates.append(path)
        for pattern in ("modules/*.jsonl", "ros/*.log", "ros/*.stdout.log", "ros/*.stderr.log"):
            candidates.extend(sorted(self.log_dir.glob(pattern)))
        return candidates

    def _report(self, severity: str, *, event: str, message: str, details: dict[str, Any] | None = None) -> None:
        try:
            reporter = self.reporter or get_diagnostic_reporter("diagnostic_bundle")
            reporter.report(
                severity=severity,
                event=event,
                message=message,
                subsystem="observability",
                source=__name__,
                details=details or {},
            )
        except Exception:
            logger.debug("Diagnostic bundle reporting failed", exc_info=True)
