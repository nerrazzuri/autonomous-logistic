from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.observability.diagnostic_bundle import DiagnosticBundleBuilder


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a sanitized diagnostic bundle zip.")
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--output-dir", default="diagnostics")
    parser.add_argument("--name")
    parser.add_argument("--max-file-bytes", type=int, default=2 * 1024 * 1024)
    parser.add_argument("--max-total-bytes", type=int, default=25 * 1024 * 1024)
    parser.add_argument("--include-digest", dest="include_digest", action="store_true", default=True)
    parser.add_argument("--no-include-digest", dest="include_digest", action="store_false")
    args = parser.parse_args()

    bundle_path = DiagnosticBundleBuilder(
        log_dir=args.log_dir,
        output_dir=args.output_dir,
        bundle_name=args.name,
        max_file_bytes=args.max_file_bytes,
        max_total_bytes=args.max_total_bytes,
        include_digest=args.include_digest,
    ).build()
    print(bundle_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
