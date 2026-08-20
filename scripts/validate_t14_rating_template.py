#!/usr/bin/env python3
"""Validate the privacy-minimised T14 steward response template."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = {
    "episode_id", "before_alias", "after_alias", "target_corrected",
    "preservation_score_1_to_5", "introduced_defect", "confidence_0_to_100",
    "uncertain", "repeat_observation",
}
SENSITIVE = {"name", "email", "phone", "address", "ip", "user_agent", "participant_id"}


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "benchmark/evidence/snapshots/t14-human-rating-response-template.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0.0":
        raise ValueError("unsupported schema_version")
    responses = payload.get("responses")
    if not isinstance(responses, list) or not responses:
        raise ValueError("responses must be a non-empty list")
    seen: set[str] = set()
    for index, row in enumerate(responses, 1):
        if not isinstance(row, dict):
            raise ValueError(f"response {index} must be an object")
        prohibited = SENSITIVE & {str(key).lower() for key in row}
        if prohibited:
            raise ValueError(f"response {index} contains prohibited fields: {sorted(prohibited)}")
        missing = REQUIRED - set(row)
        if missing:
            raise ValueError(f"response {index} missing fields: {sorted(missing)}")
        episode_id = row["episode_id"]
        if not isinstance(episode_id, str) or not episode_id or episode_id in seen:
            raise ValueError(f"response {index} has duplicate or invalid episode_id")
        seen.add(episode_id)
        preservation = row["preservation_score_1_to_5"]
        if preservation is not None and (
            not isinstance(preservation, int) or isinstance(preservation, bool) or not 1 <= preservation <= 5
        ):
            raise ValueError(f"response {index} has invalid preservation score")
        confidence = row["confidence_0_to_100"]
        if confidence is not None and (
            not isinstance(confidence, int) or isinstance(confidence, bool) or not 0 <= confidence <= 100
        ):
            raise ValueError(f"response {index} has invalid confidence")
        for field in ("target_corrected", "introduced_defect", "uncertain", "repeat_observation"):
            if row[field] is not None and not isinstance(row[field], bool):
                raise ValueError(f"response {index} field {field} must be boolean or null")
    privacy = payload.get("privacy")
    if not isinstance(privacy, dict) or privacy.get("direct_identifiers") is not False:
        raise ValueError("privacy.direct_identifiers must be false")
    print(f"T14 response template valid: {len(responses)} episode(s), status={payload.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
