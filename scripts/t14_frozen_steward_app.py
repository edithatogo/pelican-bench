#!/usr/bin/env python3
"""Validate or serve the authorization-gated frozen T14 rating session."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import socketserver
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from pelicanbench.t14_rating import (
    FrozenRatingSession,
    HashChainedRatingLedger,
    canonical_bytes,
    load_frozen_rating_session,
    validate_rating_authorization,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = ROOT / "benchmark/evidence/advisory/t14/pending-freeze-decision.json"
DEFAULT_FREEZE = ROOT / "benchmark/evidence/advisory/t14/procedural-freeze-decision-receipt.json"
DEFAULT_CANDIDATE = ROOT / "benchmark/fixtures/repair/candidate/manifest.json"
INTERFACE_VERSION = "t14-frozen-steward-local-v1"

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>T14 frozen steward rating</title><style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#17202a;background:#fafafa}.notice{background:#fff3cd;border:1px solid #e0c36a;padding:1rem;border-radius:8px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:1rem}.card,.controls{background:white;border:1px solid #ccd3da;border-radius:8px;padding:1rem}.card img{width:100%;height:360px;object-fit:contain}.controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:1rem;margin-top:1rem}label{display:flex;flex-direction:column;gap:.3rem}button{padding:.7rem 1rem;background:#1457a6;color:white;border:0;border-radius:6px}</style></head><body><h1>T14 frozen steward rating</h1><div class="notice"><strong>Blinded assignment.</strong> Do not seek source labels, duplicate identities, held-out allocation, automatic scores, or agent advice. Each save is appended locally and cannot be overwritten.</div><p id="progress"></p><div class="pair"><div class="card"><h2>Before</h2><img id="before" alt="Blinded before render"></div><div class="card"><h2>After</h2><img id="after" alt="Blinded after render"></div></div><form id="rating" class="controls"><label>Target corrected?<select name="target_corrected" required><option value="">Choose</option><option value="true">Yes</option><option value="false">No</option><option value="null">Uncertain</option></select></label><label>Preservation score (1-5)<select name="preservation_score_1_to_5" required><option value="">Choose</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label><label>Introduced defect?<select name="introduced_defect" required><option value="">Choose</option><option value="true">Yes</option><option value="false">No</option><option value="null">Uncertain</option></select></label><label>Confidence (0-100)<input name="confidence_0_to_100" type="number" min="0" max="100" required></label><label>Uncertain overall?<select name="uncertain" required><option value="">Choose</option><option value="true">Yes</option><option value="false">No</option></select></label><button type="submit">Append response</button></form><p id="message"></p><script>const assignments=__ASSIGNMENTS__,start=__START__;let index=start;function value(v){return v==='null'?null:v==='true'?true:v==='false'?false:Number(v)}function render(){if(index>=assignments.length){document.querySelector('#progress').textContent='All assignments are complete.';document.querySelector('#rating').hidden=true;return}document.querySelector('#progress').textContent=`Assignment ${index+1} of ${assignments.length}`;document.querySelector('#before').src=`/asset/${index}/before`;document.querySelector('#after').src=`/asset/${index}/after`}document.querySelector('#rating').addEventListener('submit',async event=>{event.preventDefault();const form=new FormData(event.target),row={assignment_alias:assignments[index].assignment_alias,target_corrected:value(form.get('target_corrected')),preservation_score_1_to_5:value(form.get('preservation_score_1_to_5')),introduced_defect:value(form.get('introduced_defect')),confidence_0_to_100:value(form.get('confidence_0_to_100')),uncertain:value(form.get('uncertain'))};const response=await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(row)});const result=await response.json();if(!response.ok){document.querySelector('#message').textContent=result.error||'Save failed';return}index=result.completed;event.target.reset();document.querySelector('#message').textContent=result.message;render()});render();</script></body></html>"""


def _outside_repository(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("frozen rating outputs must remain outside the repository")
    return resolved


def _final_payload(
    session: FrozenRatingSession,
    rows: list[dict[str, Any]],
    authorization: dict[str, Any],
    authorization_sha256: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "2.0.0",
        "study_id": session.study_id,
        "status": (
            "qualification-submitted"
            if authorization["rating_route"] == "qualification"
            else "steward-submitted"
        ),
        "rating_route": authorization["rating_route"],
        "assignment_limit": authorization["assignment_limit"],
        "rater_role": "benchmark-steward",
        "interface_version": INTERFACE_VERSION,
        "freeze_receipt_sha256": session.freeze_receipt_sha256,
        "candidate_manifest_sha256": session.candidate_manifest_sha256,
        "alias_manifest_sha256": session.alias_manifest_sha256,
        "assignment_manifest_sha256": session.assignment_manifest_sha256,
        "rating_authorization_sha256": authorization_sha256,
        "responses": rows,
        "privacy": {"direct_identifiers": False, "free_text": False},
        "classification": {"human": True, "independent": False, "normative": False},
        "authority_effect": {
            "ratings": True,
            "score_promotion": False,
            "attestation": False,
            "release": False,
            "publication": False,
            "unblinding": False,
        },
    }
    unsigned = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["response_sha256"] = hashlib.sha256(unsigned).hexdigest()
    return payload


class RatingServer(socketserver.TCPServer):
    session: FrozenRatingSession
    assignments: tuple[dict[str, Any], ...]
    public_assignments: tuple[dict[str, str], ...]
    authorization: dict[str, Any]
    authorization_sha256: str
    ledger: HashChainedRatingLedger
    output: Path


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "T14FrozenSteward/1.0"

    @property
    def rating_server(self) -> RatingServer:
        return cast(RatingServer, self.server)

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            start = len(self.rating_server.ledger.latest_rows())
            body = HTML.replace(
                "__ASSIGNMENTS__", json.dumps(self.rating_server.public_assignments)
            ).replace("__START__", str(start))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())
            return
        parts = route.strip("/").split("/")
        if (
            len(parts) == 3
            and parts[0] == "asset"
            and parts[1].isdigit()
            and parts[2] in {"before", "after"}
        ):
            index = int(parts[1])
            if index < len(self.rating_server.assignments):
                path = Path(self.rating_server.assignments[index]["_" + parts[2]])
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.end_headers()
                self.wfile.write(path.read_bytes())
                return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/save":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16_384:
                raise ValueError("rating request size is invalid")
            row_value = json.loads(self.rfile.read(length))
            if not isinstance(row_value, dict):
                raise ValueError("rating request must be an object")
            row = cast(dict[str, Any], row_value)
            completed = len(self.rating_server.ledger.latest_rows())
            expected = self.rating_server.assignments[completed]["assignment_alias"]
            if row.get("assignment_alias") != expected:
                raise ValueError("assignment is not the next frozen item")
            self.rating_server.ledger.append(row, saved_at=datetime.now(UTC).isoformat())
            rows = self.rating_server.ledger.latest_rows()
            if len(rows) == len(self.rating_server.assignments):
                payload = _final_payload(
                    self.rating_server.session,
                    rows,
                    self.rating_server.authorization,
                    self.rating_server.authorization_sha256,
                )
                self.rating_server.output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                self.rating_server.output.parent.chmod(0o700)
                with self.rating_server.output.open("xb") as handle:
                    handle.write(canonical_bytes(payload))
                self.rating_server.output.chmod(0o600)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"completed": len(rows), "message": "Response appended locally."}
                ).encode()
            )
        except (IndexError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--freeze-receipt", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--restricted-alias-manifest", type=Path, required=True)
    parser.add_argument("--restricted-assignment-manifest", type=Path, required=True)
    parser.add_argument("--rating-authorization", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    session = load_frozen_rating_session(
        root=ROOT,
        packet_path=args.packet.resolve(),
        freeze_receipt_path=args.freeze_receipt.resolve(),
        candidate_path=args.candidate.resolve(),
        alias_path=args.restricted_alias_manifest.resolve(),
        assignment_path=args.restricted_assignment_manifest.resolve(),
    )
    if not args.serve:
        print(
            json.dumps(
                {
                    "status": "ready-not-authorized",
                    "assignments": 106,
                    "source_episodes": 96,
                    "duplicates": 10,
                    "ratings_started": False,
                    "unblinded": False,
                }
            )
        )
        return 0
    if args.rating_authorization is None or args.ledger is None or args.output is None:
        raise ValueError("--serve requires rating authorization, ledger, and output paths")
    authorization_path = args.rating_authorization.resolve()
    authorization = validate_rating_authorization(authorization_path, session)
    authorization_sha256 = hashlib.sha256(authorization_path.read_bytes()).hexdigest()
    assignments = session.assignments[: authorization["assignment_limit"]]
    ledger = HashChainedRatingLedger(
        _outside_repository(args.ledger), {row["assignment_alias"] for row in assignments}
    )
    output = _outside_repository(args.output)
    with RatingServer(("127.0.0.1", args.port), Handler) as server:
        server.session = session
        server.assignments = assignments
        server.public_assignments = tuple(
            {"assignment_alias": row["assignment_alias"]} for row in assignments
        )
        server.authorization = authorization
        server.authorization_sha256 = authorization_sha256
        server.ledger = ledger
        server.output = output
        print(f"T14 frozen steward interface: http://127.0.0.1:{args.port}/")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
