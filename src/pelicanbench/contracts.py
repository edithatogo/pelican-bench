"""Consumer-driven contracts for model, environment, and study boundaries.

The contracts are intentionally data-driven. A provider implementation may change its
internal code, but it must continue to satisfy the versioned request and response shapes
consumed by PelicanBench.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .io import content_hash, read_json

ContractSide = Literal["request", "response", "event"]


class ContractDocument(BaseModel):
    """A frozen consumer-driven contract and its JSON Schema surfaces."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = Field(pattern=r"^contract:[a-z0-9][a-z0-9._-]*$")
    schema_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    provider: str
    consumer: str = "pelicanbench"
    description: str
    request_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    event_schema: dict[str, Any] | None = None
    required_consumer_assertions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def at_least_one_surface(self) -> ContractDocument:
        if (
            self.request_schema is None
            and self.response_schema is None
            and self.event_schema is None
        ):
            raise ValueError("a contract must define at least one schema surface")
        return self

    @property
    def digest(self) -> str:
        return content_hash(self.model_dump(mode="json"))

    def schema_for(self, side: ContractSide) -> dict[str, Any]:
        value = getattr(self, f"{side}_schema")
        if value is None:
            raise ValueError(f"contract does not define a {side} schema")
        return cast(dict[str, Any], value)


@dataclass(frozen=True, slots=True)
class ContractVerification:
    contract_id: str
    contract_digest: str
    side: ContractSide
    valid: bool
    errors: tuple[str, ...]
    payload_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_digest": self.contract_digest,
            "side": self.side,
            "valid": self.valid,
            "errors": list(self.errors),
            "payload_hash": self.payload_hash,
        }


def load_contract(path: str | Path) -> ContractDocument:
    """Load a contract and fail early if any embedded JSON Schema is malformed."""

    document = ContractDocument.model_validate(read_json(path))
    for side in ("request", "response", "event"):
        schema = getattr(document, f"{side}_schema")
        if schema is not None:
            Draft202012Validator.check_schema(schema)
    return document


def _format_validation_error(error: ValidationError) -> str:
    location = "/".join(str(item) for item in error.absolute_path) or "$"
    return f"{location}: {error.message}"


def verify_contract_payload(
    contract: ContractDocument,
    side: ContractSide,
    payload: Mapping[str, Any] | list[Any],
) -> ContractVerification:
    """Verify one producer payload against the exact consumer contract surface."""

    validator = Draft202012Validator(contract.schema_for(side))
    errors = tuple(
        _format_validation_error(error)
        for error in sorted(
            validator.iter_errors(payload), key=lambda item: list(item.absolute_path)
        )
    )
    return ContractVerification(
        contract_id=contract.contract_id,
        contract_digest=contract.digest,
        side=side,
        valid=not errors,
        errors=errors,
        payload_hash=content_hash(payload),
    )


def validate_contract_directory(path: str | Path) -> tuple[ContractDocument, ...]:
    """Load every JSON contract in lexical order and reject duplicate identifiers."""

    directory = Path(path)
    contracts: list[ContractDocument] = []
    identifiers: set[str] = set()
    for contract_path in sorted(directory.glob("*.json")):
        contract = load_contract(contract_path)
        if contract.contract_id in identifiers:
            raise ValueError(f"duplicate contract identifier: {contract.contract_id}")
        identifiers.add(contract.contract_id)
        contracts.append(contract)
    if not contracts:
        raise ValueError(f"no contracts found in {directory}")
    return tuple(contracts)


__all__ = [
    "ContractDocument",
    "ContractSide",
    "ContractVerification",
    "SchemaError",
    "load_contract",
    "validate_contract_directory",
    "verify_contract_payload",
]
