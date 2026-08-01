#!/usr/bin/env python3
"""Verify that callable Conductor skills mirror the workspace plugin snapshot."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / '.agents/plugins/conductor/skills'
DIRECT = ROOT / '.agents/skills'

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    errors: list[str] = []
    for source in sorted(PLUGIN.glob('*/SKILL.md')):
        target = DIRECT / source.parent.name / 'SKILL.md'
        if args.check:
            if not target.exists() or digest(source) != digest(target):
                errors.append(source.parent.name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    if errors:
        print('Conductor skill mirrors differ: ' + ', '.join(errors))
        return 1
    print('Conductor skill mirrors are synchronized.')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
