#!/usr/bin/env python3
"""Generate restricted T14 custody artifacts after an accountable acknowledgement."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pelicanbench.t14_custody import (  # ruff: ignore[module-import-not-at-top-of-file]
    build_restricted_custody_artifacts,
    write_new_private_file,
)
from pelicanbench.timeutil import utc_now_iso  # ruff: ignore[module-import-not-at-top-of-file]

CANDIDATE = ROOT / "benchmark/fixtures/repair/candidate/manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--secret-environment", required=True)
    parser.add_argument("--custodian-id", required=True)
    parser.add_argument(
        "--custody-classification",
        choices=("independent-custody", "procedural-self-custody-not-independent"),
        required=True,
    )
    parser.add_argument("--acknowledge-accountable-custodian", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.acknowledge_accountable_custodian:
        raise SystemExit("accountable custodian acknowledgement is required")
    secret_value = os.environ.get(args.secret_environment)
    if not secret_value:
        raise SystemExit("required custody secret environment variable is unset")
    requested_output = args.output_directory.expanduser()
    if requested_output.is_symlink():
        raise SystemExit("restricted custody output must not be a symbolic link")
    output = requested_output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise SystemExit("restricted custody output must be outside the repository")
    if output.exists() and any(output.iterdir()):
        raise SystemExit("restricted custody output directory must be absent or empty")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    output.chmod(0o700)
    if output.stat().st_mode & 0o777 != 0o700:
        raise SystemExit("restricted custody output directory must have mode 0700")

    candidate_bytes = CANDIDATE.read_bytes()
    alias_manifest, duplicate_schedule, receipt = build_restricted_custody_artifacts(
        json.loads(candidate_bytes),
        candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        secret=secret_value.encode(),
        custodian_id=args.custodian_id,
        custody_classification=args.custody_classification,
        created_at=utc_now_iso(),
    )
    write_new_private_file(output / "restricted-alias-manifest.json", alias_manifest)
    write_new_private_file(output / "restricted-duplicate-schedule.json", duplicate_schedule)
    write_new_private_file(output / "custody-receipt.json", receipt)
    print(
        json.dumps(
            {
                "status": "generated-no-gate-effect",
                "output_directory": str(output),
                "custody_receipt_sha256": hashlib.sha256(
                    (output / "custody-receipt.json").read_bytes()
                ).hexdigest(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
