"""Compact summaries for structured diagnostics logs and diagnostic bundles."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
import json
from pathlib import Path
from typing import Any
import zipfile

from shared.diagnostics.redaction import redact_mapping, redact_value


def _safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return dict(redact_mapping(value))


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return repr(value)


def _structured_members_from_bundle(archive: zipfile.ZipFile) -> list[str]:
    names = set(archive.namelist())
    if "logs/app.jsonl" in names:
        return ["logs/app.jsonl"]
    return sorted(
        name
        for name in names
        if name.startswith("logs/modules/") and name.endswith(".jsonl")
    )


def _structured_files_from_log_dir(log_dir: Path) -> list[Path]:
    app_jsonl = log_dir / "app.jsonl"
    if app_jsonl.is_file():
        return [app_jsonl]
    return sorted((log_dir / "modules").glob("*.jsonl"))


def _read_lines_from_bundle(archive: zipfile.ZipFile, member: str) -> list[str]:
    return archive.read(member).decode("utf-8").splitlines()


def _read_lines_from_file(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _compact_event(record: Mapping[str, Any]) -> dict[str, Any]:
    details = record.get("details")
    if isinstance(details, Mapping):
        details = _safe_mapping(details)
    else:
        details = _json_safe(redact_value(details))

    context = record.get("context")
    if isinstance(context, Mapping):
        context = _safe_mapping(context)
    else:
        context = _json_safe(redact_value(context))

    return {
        "ts": record.get("ts"),
        "level": record.get("level"),
        "module": record.get("module"),
        "event": record.get("event"),
        "error_code": record.get("error_code"),
        "message": record.get("message"),
        "context": context,
        "details": details,
    }


def _iter_records(lines: Iterable[str]) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    malformed = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(data, dict):
            malformed += 1
            continue
        records.append(data)
    return records, malformed


def _latest_sorted(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda item: str(item.get("ts") or ""), reverse=True)


def _status_summary_from_bundle(archive: zipfile.ZipFile) -> dict[str, Any] | None:
    try:
        raw = json.loads(archive.read("generated/status_summary.json").decode("utf-8"))
    except KeyError:
        return None
    if not isinstance(raw, dict):
        return None
    diagnostics = raw.get("diagnostics")
    alerts = raw.get("alerts")
    return {
        "status": raw.get("status"),
        "diagnostics_error_count": diagnostics.get("error_count") if isinstance(diagnostics, dict) else None,
        "alert_count": alerts.get("active_count") if isinstance(alerts, dict) else None,
    }


def _status_summary_from_log_dir(log_dir: Path) -> dict[str, Any] | None:
    path = log_dir / "status_summary.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    diagnostics = raw.get("diagnostics")
    alerts = raw.get("alerts")
    return {
        "status": raw.get("status"),
        "diagnostics_error_count": diagnostics.get("error_count") if isinstance(diagnostics, dict) else None,
        "alert_count": alerts.get("active_count") if isinstance(alerts, dict) else None,
    }


def _warnings_from_manifest_bundle(archive: zipfile.ZipFile) -> list[str]:
    try:
        manifest = json.loads(archive.read("generated/manifest.json").decode("utf-8"))
    except KeyError:
        return []
    warnings: list[str] = []
    for entry in manifest.get("files", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("truncated"):
            warnings.append(f"truncated: {entry.get('archive_path')}")
        if entry.get("included") is False and entry.get("reason"):
            warnings.append(f"skipped: {entry.get('archive_path')} ({entry.get('reason')})")
    return warnings


def build_log_digest(
    *,
    log_dir: str | Path = "logs",
    bundle_path: str | Path | None = None,
    max_events: int = 100,
) -> dict[str, Any]:
    """Build a compact JSON-safe summary for diagnostics logs or a bundle zip."""

    if max_events <= 0:
        max_events = 100

    records: list[dict[str, Any]] = []
    malformed_lines = 0
    warnings: list[str] = []
    status_summary: dict[str, Any] | None = None
    source_files: list[str] = []

    if bundle_path is not None:
        with zipfile.ZipFile(bundle_path) as archive:
            members = _structured_members_from_bundle(archive)
            if not members:
                warnings.append("no structured logs found in bundle")
            for member in members:
                source_files.append(member)
                chunk, malformed = _iter_records(_read_lines_from_bundle(archive, member))
                records.extend(chunk)
                malformed_lines += malformed
            status_summary = _status_summary_from_bundle(archive)
            warnings.extend(_warnings_from_manifest_bundle(archive))
    else:
        base_dir = Path(log_dir)
        files = _structured_files_from_log_dir(base_dir)
        if not files:
            warnings.append("no structured logs found")
        for path in files:
            source_files.append(str(path))
            chunk, malformed = _iter_records(_read_lines_from_file(path))
            records.extend(chunk)
            malformed_lines += malformed
        status_summary = _status_summary_from_log_dir(base_dir)

    levels = Counter(str(record.get("level") or "UNKNOWN") for record in records)
    modules = Counter(str(record.get("module") or "unknown") for record in records)
    error_codes = Counter(str(record.get("error_code")) for record in records if record.get("error_code"))
    error_records = [
        record for record in records if str(record.get("level") or "").upper() in {"ERROR", "CRITICAL"}
    ]
    latest_errors = [_compact_event(record) for record in error_records[:max_events]]
    latest_critical = next(
        (_compact_event(record) for record in _latest_sorted(records) if str(record.get("level") or "").upper() == "CRITICAL"),
        None,
    )

    process_events = Counter(str(record.get("event") or "") for record in records if str(record.get("event") or "").startswith("process."))
    summary = {
        "overall": {
            "total_structured_events": len(records),
            "malformed_lines": malformed_lines,
            "levels": dict(levels),
            "modules": dict(modules),
            "error_codes": dict(error_codes),
            "sources": source_files,
        },
        "latest_errors": latest_errors,
        "diagnostics": {
            "error_count": len(error_records),
            "latest_critical": latest_critical,
        },
        "process": {
            "started": process_events.get("process.started", 0),
            "exited": process_events.get("process.exited", 0),
            "failed": process_events.get("process.failed", 0),
            "nonzero_exits": error_codes.get("process.exited_nonzero", 0),
        },
        "status_summary": status_summary,
        "warnings": warnings,
    }
    if malformed_lines:
        summary["warnings"].append(f"malformed JSONL lines: {malformed_lines}")
    return summary


def render_log_digest_markdown(summary: Mapping[str, Any]) -> str:
    """Render a human-readable Markdown digest."""

    overall = summary.get("overall", {})
    process = summary.get("process", {})
    status_summary = summary.get("status_summary")
    lines = [
        "# Log Digest",
        "",
        f"- Total structured events: {overall.get('total_structured_events', 0)}",
        f"- Malformed JSONL lines: {overall.get('malformed_lines', 0)}",
        "",
        "## Levels",
    ]
    for level, count in sorted((overall.get("levels") or {}).items()):
        lines.append(f"- {level}: {count}")

    lines.extend(["", "## Modules"])
    for module, count in sorted((overall.get("modules") or {}).items()):
        lines.append(f"- {module}: {count}")

    lines.extend(
        [
            "",
            "## Process Summary",
            f"- process.started: {process.get('started', 0)}",
            f"- process.exited: {process.get('exited', 0)}",
            f"- process.failed: {process.get('failed', 0)}",
            f"- non-zero exits: {process.get('nonzero_exits', 0)}",
        ]
    )

    if status_summary:
        lines.extend(
            [
                "",
                "## Status Summary",
                f"- status: {status_summary.get('status')}",
                f"- diagnostics error count: {status_summary.get('diagnostics_error_count')}",
                f"- alert count: {status_summary.get('alert_count')}",
            ]
        )

    lines.extend(["", "## Latest Errors"])
    latest_errors = summary.get("latest_errors") or []
    if not latest_errors:
        lines.append("- none")
    else:
        for item in latest_errors[:10]:
            lines.append(
                f"- {item.get('ts')} [{item.get('module')}] {item.get('event')} "
                f"({item.get('error_code')}): {item.get('message')}"
            )
            if item.get("details") not in (None, {}, []):
                lines.append(f"  - details: `{json.dumps(item.get('details'), sort_keys=True)}`")
            if item.get("context") not in (None, {}, []):
                lines.append(f"  - context: `{json.dumps(item.get('context'), sort_keys=True)}`")

    warnings = summary.get("warnings") or []
    if warnings:
        lines.extend(["", "## Warnings"])
        for warning in warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines) + "\n"
