"""Time helpers with reproducibility support."""
from __future__ import annotations
import os
from datetime import UTC, datetime

def utc_now() -> datetime:
    epoch = os.getenv("SOURCE_DATE_EPOCH")
    if epoch is not None:
        return datetime.fromtimestamp(int(epoch), tz=UTC)
    return datetime.now(tz=UTC)

def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")
