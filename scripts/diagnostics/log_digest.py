from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.observability.log_digest import build_log_digest, render_log_digest_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact digest from diagnostics logs or a bundle.")
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--bundle")
    parser.add_argument("--output")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()

    summary = build_log_digest(log_dir=args.log_dir, bundle_path=args.bundle)
    if args.format == "json":
        rendered = json.dumps(summary, indent=2, sort_keys=True)
    else:
        rendered = render_log_digest_markdown(summary)

    print(rendered, end="" if rendered.endswith("\n") else "\n")
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
