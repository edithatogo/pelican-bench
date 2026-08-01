"""Non-duplicative integration boundaries for Dylan Mordaunt's repository ecosystem."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Integration:
    repository: str
    capability: str
    direction: str
    required: bool
    contract: str


INTEGRATIONS = (
    Integration("edithatogo/krita-cli", "legacy agentic drawing adapter", "import", False, "MCP/CLI adapter"),
    Integration("edithatogo/sourceright", "source rights and provenance", "bidirectional", False, "rights-record exchange"),
    Integration("edithatogo/authentext", "text authenticity and attestations", "bidirectional", False, "content-hash and attestation exchange"),
    Integration("edithatogo/open_social_data", "human preference and public annotation data", "import", False, "Arrow/Parquet dataset"),
    Integration("edithatogo/osf-cli-go", "preregistration and archival publication", "export", False, "release bundle"),
    Integration("edithatogo/voiage", "evaluation and value-of-information methods", "bidirectional", False, "versioned analysis contract"),
    Integration("edithatogo/entireio-cli", "agent provenance experiments", "optional comparison", False, "CLI boundary"),
)


def locate_sibling_repositories(root: str | Path, integrations: Iterable[Integration] = INTEGRATIONS) -> dict[str, str | None]:
    parent = Path(root).resolve().parent
    output: dict[str, str | None] = {}
    for integration in integrations:
        name = integration.repository.rsplit("/", 1)[-1]
        candidate = parent / name
        output[integration.repository] = candidate.as_posix() if candidate.is_dir() else None
    return output
