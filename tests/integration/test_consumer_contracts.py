from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from pelicanbench.adapters import OpenAICompatibleAdapter
from pelicanbench.canvas import CanvasEnvironment
from pelicanbench.contracts import (
    ContractDocument,
    load_contract,
    validate_contract_directory,
    verify_contract_payload,
)
from pelicanbench.environments import PelicanCanvasOpenEnv

pytestmark = [pytest.mark.integration, pytest.mark.contract]


def test_contract_directory_is_unique_and_schema_valid(root: Path) -> None:
    contracts = validate_contract_directory(root / "benchmark/contracts")
    assert {contract.contract_id for contract in contracts} == {
        "contract:campaign-worker-execution-v1",
        "contract:human-rating-exchange-v1",
        "contract:openai-compatible-chat-v1",
        "contract:openai-compatible-stream-v1",
        "contract:pelican-canvas-openenv-v1",
    }
    assert len({contract.digest for contract in contracts}) == len(contracts)


def test_contract_document_requires_a_schema_surface() -> None:
    with pytest.raises(ValueError, match="at least one schema"):
        ContractDocument(
            contract_id="contract:empty",
            schema_version="1.0.0",
            provider="provider",
            description="invalid",
        )


def test_openenv_provider_satisfies_event_contract(root: Path) -> None:
    contract = load_contract(root / "benchmark/contracts/pelican-canvas-openenv.json")
    environment = PelicanCanvasOpenEnv(CanvasEnvironment())
    action = {
        "type": "add",
        "id": "wheel",
        "element": {"tag": "circle", "attributes": {"cx": 20, "cy": 20, "r": 10}},
    }
    request_result = verify_contract_payload(contract, "request", action)
    response = json.loads(json.dumps(environment.step(action)))
    response_result = verify_contract_payload(contract, "event", response)
    assert request_result.valid, request_result.errors
    assert response_result.valid, response_result.errors


def test_human_exchange_contract_rejects_direct_identifier(root: Path) -> None:
    contract = load_contract(root / "benchmark/contracts/human-rating-exchange.json")
    valid = {
        "task_id": "task-1",
        "criterion": "overall-preference",
        "left_artifact_id": "artifact-a",
        "right_artifact_id": "artifact-b",
        "winner": "A",
        "rater_hash": "0123456789abcdef",
    }
    assert verify_contract_payload(contract, "event", valid).valid
    invalid = {**valid, "email": "participant@example.org"}
    result = verify_contract_payload(contract, "event", invalid)
    assert not result.valid
    assert any("Additional properties" in error for error in result.errors)


def test_openai_adapter_against_consumer_driven_contract(root: Path, heritage) -> None:
    contract = load_contract(root / "benchmark/contracts/openai-compatible-chat.json")
    observed: dict[str, Any] = {}
    provider_response = {
        "choices": [
            {
                "message": {"content": "<svg xmlns='http://www.w3.org/2000/svg'></svg>"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 12},
    }
    assert verify_contract_payload(contract, "response", provider_response).valid

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            payload = json.loads(self.rfile.read(length))
            observed["payload"] = payload
            verification = verify_contract_payload(contract, "request", payload)
            if not verification.valid:
                self.send_response(422)
                self.end_headers()
                return
            body = json.dumps(provider_response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *args: object) -> None:
            del args

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        adapter = OpenAICompatibleAdapter(
            f"http://127.0.0.1:{server.server_port}",
            adapter_id="contract-test",
            model_id="provider/model",
            model_revision="immutable-revision",
        )
        result = adapter.generate(heritage, seed=17)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert result.output.startswith("<svg")
    request_result = verify_contract_payload(contract, "request", observed["payload"])
    assert request_result.valid, request_result.errors
    messages = observed["payload"]["messages"]
    assert any(
        message["role"] == "user" and heritage.prompt in message["content"] for message in messages
    )


def test_campaign_worker_records_satisfy_consumer_contract(root: Path) -> None:
    contract = load_contract(root / "benchmark/contracts/campaign-worker-execution.json")
    source = root / "benchmark/evidence/snapshots/campaign-execution-records-fixture.jsonl"
    records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    assert records
    for record in records:
        result = verify_contract_payload(contract, "event", record)
        assert result.valid, result.errors

    invalid = dict(records[0])
    invalid.pop("attempt")
    result = verify_contract_payload(contract, "event", invalid)
    assert not result.valid
    assert any("attempt" in error for error in result.errors)
