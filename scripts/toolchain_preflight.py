#!/usr/bin/env python3
"""Record local and CI quality-tool availability without overstating verification."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

TOOLS = {
    "ruff": {"kind": "executable", "required_in_ci": True},
    "mypy": {"kind": "module", "required_in_ci": True},
    "pyright": {"kind": "executable", "required_in_ci": True},
    "vale": {"kind": "executable", "required_in_ci": True},
    "hypothesis": {"kind": "module", "required_in_ci": True},
    "mutmut": {"kind": "executable", "required_in_ci": False},
    "cargo": {"kind": "executable", "required_in_ci": True},
    "mojo": {"kind": "executable", "required_in_ci": False},
    "entire": {"kind": "executable", "required_in_ci": False},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="artifacts/toolchain-preflight.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    records = []
    for name, policy in TOOLS.items():
        if policy["kind"] == "module":
            available = importlib.util.find_spec(name) is not None
            location = None
        else:
            location = shutil.which(name)
            available = location is not None
        records.append(
            {
                "tool": name,
                "kind": policy["kind"],
                "available_locally": available,
                "location": location,
                "required_in_ci": policy["required_in_ci"],
                "verification_state": "locally-runnable" if available else "deferred-to-ci",
            }
        )
    payload = {
        "schema_version": "1.0.0",
        "tools": records,
        "local_tools_available": sum(item["available_locally"] for item in records),
        "missing_ci_tools": [
            item["tool"]
            for item in records
            if item["required_in_ci"] and not item["available_locally"]
        ],
        "claim": (
            "Missing local tools are not represented as having passed; "
            "repository-native fallbacks run separately."
        ),
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
