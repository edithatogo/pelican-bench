#!/usr/bin/env python3
"""Run the local, blinded T14 steward-rating interface.

This is intentionally a small standard-library application: it serves only the
project-original repair fixtures named by the blinded manifest and writes the
existing privacy-minimised response shape.  It is not a labelling service or a
source of human evidence; the steward's submitted file is the authoritative
input and must still be reviewed and hash-bound.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import secrets
import socketserver
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "benchmark/evidence/snapshots/t14-blinded-pilot-manifest.json"
DEFAULT_OUTPUT = ROOT / "benchmark/evidence/snapshots/t14-human-rating-response.json"
INTERFACE_VERSION = "t14-steward-local-v1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest(path: Path) -> tuple[dict, str, list[dict]]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if payload.get("status") != "development-only" or payload.get("source_labels_exposed"):
        raise ValueError("manifest is not a blinded development manifest")
    episodes = payload.get("episodes")
    if not isinstance(episodes, list) or not episodes:
        raise ValueError("manifest has no episodes")
    tasks = {row["repair_id"]: row for row in json.loads(
        (ROOT / "benchmark/fixtures/repair/tasks.json").read_text(encoding="utf-8")
    )}
    for episode in episodes:
        task = tasks.get(episode.get("episode_id"))
        if not task:
            raise ValueError(f"no fixture task for {episode.get('episode_id')}")
        for key in ("before", "after_reference"):
            fixture = (ROOT / task[key]).resolve()
            if ROOT not in fixture.parents or not fixture.is_file():
                raise ValueError(f"fixture is outside repository or missing: {fixture}")
        episode["_before"] = str((ROOT / task["before"]).resolve())
        episode["_after"] = str((ROOT / task["after_reference"]).resolve())
    return payload, sha256_bytes(raw), episodes


def response_template(manifest: dict, manifest_hash: str, episodes: list[dict]) -> dict:
    return {
        "schema_version": "1.0.0",
        "study_id": manifest["study_id"],
        "manifest": "benchmark/evidence/snapshots/t14-blinded-pilot-manifest.json",
        "manifest_sha256": manifest_hash,
        "interface_version": INTERFACE_VERSION,
        "status": "steward-submitted",
        "rater_role": "benchmark-steward",
        "responses": [
            {
                "episode_id": row["episode_id"],
                "before_alias": row["before_alias"],
                "after_alias": row["after_alias"],
                "target_corrected": row.get("target_corrected"),
                "preservation_score_1_to_5": row.get("preservation_score_1_to_5"),
                "introduced_defect": row.get("introduced_defect"),
                "confidence_0_to_100": row.get("confidence_0_to_100"),
                "uncertain": row.get("uncertain"),
                "repeat_observation": row.get("repeat_observation"),
            }
            for row in episodes
        ],
        "privacy": {"direct_identifiers": False, "free_text": False, "rater_hash": None},
        "limitations": [
            "This is a two-episode development rehearsal, not the prespecified held-out calibration.",
            "Agent analysis cannot supply missing ratings or constitute independent approval.",
        ],
    }


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>T14 steward rating</title>
<style>
body{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#17202a;background:#fafafa}
.notice{background:#fff3cd;border:1px solid #e0c36a;padding:1rem;border-radius:8px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:1rem}.card{background:white;border:1px solid #ccd3da;border-radius:8px;padding:.75rem}.card img{width:100%;height:360px;object-fit:contain;background:#fff}.controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;background:white;border:1px solid #ccd3da;border-radius:8px;padding:1rem;margin-top:1rem}label{display:flex;flex-direction:column;gap:.3rem}button{font-size:1rem;padding:.7rem 1rem;border:0;border-radius:6px;background:#1457a6;color:white}button:disabled{opacity:.5}#message{margin-top:1rem;font-weight:600}.hidden{display:none}
</style></head><body>
<h1>T14 steward rating</h1>
<div class="notice"><strong>Blinded development rehearsal.</strong> This local interface shows only canonical before/after renders. It does not show source labels, expected outcomes, automatic scores, or agent advice. Your submitted JSON is advisory evidence until you review and accept it.</div>
<p><a href="/instructions" target="_blank">Open instructions in another tab</a></p>
<p id="progress"></p><section id="episode"></section>
<form id="rating" class="controls" onsubmit="return next(event)">
<label>Target corrected?<select name="target_corrected" required><option value="">Choose…</option><option value="true">Yes</option><option value="false">No</option><option value="null">Uncertain</option></select></label>
<label>Preservation score (1–5)<select name="preservation_score_1_to_5" required><option value="">Choose…</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
<label>Introduced defect?<select name="introduced_defect" required><option value="">Choose…</option><option value="true">Yes</option><option value="false">No</option><option value="null">Uncertain</option></select></label>
<label>Confidence (0–100)<input name="confidence_0_to_100" type="number" min="0" max="100" required></label>
<label>Uncertain overall?<select name="uncertain" required><option value="">Choose…</option><option value="true">Yes</option><option value="false">No</option></select></label>
<label>Repeat observation?<select name="repeat_observation" required><option value="">Choose…</option><option value="true">Yes</option><option value="false">No</option><option value="null">Not requested</option></select></label>
<div><button id="submit" type="submit">Save response</button></div></form><p id="message"></p>
<script>
const episodes=__EPISODES__;let index=0, responses=[];
function render(){const e=episodes[index];document.querySelector('#progress').textContent=`Episode ${index+1} of ${episodes.length}`;document.querySelector('#episode').innerHTML=`<div class="pair"><div class="card"><h2>Before</h2><img src="/asset/${index}/before" alt="Blinded before render"></div><div class="card"><h2>After</h2><img src="/asset/${index}/after" alt="Blinded after render"></div></div>`;document.querySelector('#submit').textContent=index+1===episodes.length?'Submit hash-bound responses':'Save response and continue';}
function val(v){return v==='null'?null:v==='true'?true:v==='false'?false:(v===''?null:Number(v));}
function next(ev){ev.preventDefault();const f=new FormData(ev.target);responses.push({episode_id:episodes[index].episode_id,before_alias:episodes[index].before_alias,after_alias:episodes[index].after_alias,target_corrected:val(f.get('target_corrected')),preservation_score_1_to_5:val(f.get('preservation_score_1_to_5')),introduced_defect:val(f.get('introduced_defect')),confidence_0_to_100:val(f.get('confidence_0_to_100')),uncertain:val(f.get('uncertain')),repeat_observation:val(f.get('repeat_observation'))});if(index<episodes.length-1){index++;ev.target.reset();render();return false;}document.querySelector('#submit').disabled=true;fetch('/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({responses})}).then(r=>r.json()).then(x=>{document.querySelector('#message').textContent=x.message||'Saved.'}).catch(e=>{document.querySelector('#message').textContent='Save failed: '+e});return false;}
render();
</script></body></html>"""


INSTRUCTIONS = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>T14 rating instructions</title><style>body{font:16px system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#17202a;line-height:1.5}section{background:#fff;border:1px solid #ccd3da;border-radius:8px;padding:1rem;margin:1rem 0}dt{font-weight:700;margin-top:.8rem}dd{margin-left:0}code{background:#eef1f4;padding:.1rem .3rem;border-radius:3px}.notice{background:#fff3cd;border:1px solid #e0c36a;padding:1rem;border-radius:8px}</style></head><body>
<h1>T14 steward-rating instructions</h1>
<div class="notice"><strong>This is a two-episode development rehearsal.</strong> You are the sole human rater. Agent suggestions, automatic scores, hidden task labels, and source identities are intentionally unavailable and must not be reconstructed or added.</div>
<section><h2>Background: why T14 exists</h2><p>T14 is the PelicanBench track for evaluating whether an image/SVG repair process can recognise a defect, correct the intended structure, preserve the correct content, and avoid creating a new defect. This matters because a repair can change many pixels and still fail visually, or make a tiny change that leaves the actual defect untouched.</p><p>The repository contains deterministic <strong>before</strong> fixtures and corresponding <strong>after</strong> repair references. You are not being asked to edit either image or invent a repair; you are judging whether the fixed repair reference visibly satisfies that benchmark intention.</p><p>The code also computes automatic artifact and pixel metrics such as edit locality and foreground retention. Those metrics can measure how much changed, but cannot by themselves establish that the intended bicycle/pelican structure was repaired or that the result looks acceptable. Your bounded ratings are the calibration check for that gap. They do not promote the metric or change the benchmark definition.</p></section>
<section><h2>What “before” and “after” mean</h2><p><strong>Before</strong> is the canonical render of the project-original repair fixture before the proposed repair. <strong>After</strong> is the corresponding canonical render after the proposed repair. Compare the two images as a single pair; do not treat the after image as a new independent drawing.</p><p>Use the visible change and the broad task intent: did the repair address the apparent structural problem while preserving the pelican, bicycle, and other correct content? If you cannot make a defensible judgment from the pair, use the uncertainty controls.</p></section>
<section><h2>What each choice means</h2><dl>
<dt>Target corrected?</dt><dd><strong>Yes</strong> means the visible intended repair appears successful. <strong>No</strong> means the defect remains or the repair does not solve it. <strong>Uncertain</strong> means the pair does not support a reliable yes/no judgment.</dd>
<dt>Preservation score (1–5)</dt><dd>Rate how much correct content and relationships were retained: <strong>1</strong> = substantial loss or distortion, <strong>3</strong> = mixed/partly preserved, <strong>5</strong> = correct content is preserved with only necessary changes.</dd>
<dt>Introduced defect?</dt><dd><strong>Yes</strong> means the after image visibly adds a new error, break, omission, or harmful change not present before. <strong>No</strong> means no new defect is apparent. <strong>Uncertain</strong> means you cannot tell.</dd>
<dt>Confidence (0–100)</dt><dd>Your confidence in the three judgments above. Use a lower value when the images are ambiguous or the distinction is hard to see.</dd>
<dt>Uncertain overall?</dt><dd>Choose <strong>Yes</strong> if any important part of the judgment is genuinely uncertain; otherwise choose <strong>No</strong>.</dd>
<dt>Repeat observation?</dt><dd>Choose <strong>Yes</strong> only if you independently rechecked the pair before submitting. Choose <strong>No</strong> if you did not perform a repeat check. <strong>Not requested</strong> is retained for episodes where no repeat was requested by the protocol.</dd>
</dl></section>
<section><h2>Workflow</h2><ol><li>Read these instructions before rating.</li><li>For each episode, inspect the before and after images side by side.</li><li>Record your first judgment without looking for hidden labels or automatic scores.</li><li>Use uncertainty rather than guessing.</li><li>After the final episode, submit once. The app writes a hash-bound JSON response locally.</li><li>Review that file before treating it as a steward decision or evidence.</li></ol></section>
<section><h2>What this page does not establish</h2><p>This interface does not create a normative score, independent review, legal approval, inter-rater agreement, or E3 evidence. The current two episodes are not a held-out calibration sample, and T14 remains P2-partial until the approved calibration and analysis gates are complete.</p></section>
<p><a href="/">Return to rating interface</a></p></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "T14Steward/1.0"

    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/":
            body = HTML.replace("__EPISODES__", json.dumps(self.server.public_episodes))
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(body.encode())
            return
        if route == "/instructions":
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(INSTRUCTIONS.encode()); return
        parts = route.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "asset" and parts[1].isdigit() and parts[2] in {"before", "after"}:
            index = int(parts[1])
            if index < len(self.server.episodes):
                path = Path(self.server.episodes[index]["_" + parts[2]])
                self.send_response(200); self.send_header("Content-Type", "image/svg+xml"); self.end_headers()
                self.wfile.write(path.read_bytes()); return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/submit": self.send_error(404); return
        try:
            length = int(self.headers.get("Content-Length", "0")); data = json.loads(self.rfile.read(length))
            expected = {e["episode_id"] for e in self.server.episodes}; rows = data.get("responses", [])
            if {r.get("episode_id") for r in rows} != expected or len(rows) != len(expected): raise ValueError("episode set does not match manifest")
            payload = response_template(self.server.manifest, self.server.manifest_hash, self.server.episodes); payload["responses"] = rows
            payload["submitted_at"] = datetime.now(timezone.utc).isoformat(); payload["submission_nonce"] = secrets.token_hex(8)
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(); payload["response_sha256"] = sha256_bytes(canonical)
            self.server.output.parent.mkdir(parents=True, exist_ok=True); self.server.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b'{"message":"Hash-bound response saved. Review it before treating it as evidence."}')
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.send_error(400, str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST); parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT); parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(); manifest, manifest_hash, episodes = load_manifest(args.manifest.resolve())
    Handler.manifest = manifest; Handler.manifest_hash = manifest_hash; Handler.episodes = episodes; Handler.output = args.output.resolve(); Handler.public_episodes = [{k: e[k] for k in ("episode_id", "before_alias", "after_alias")} for e in episodes]
    with socketserver.TCPServer(("127.0.0.1", args.port), Handler) as server:
        server.manifest = manifest; server.manifest_hash = manifest_hash; server.episodes = episodes; server.output = args.output.resolve(); server.public_episodes = Handler.public_episodes
        print(f"T14 steward interface: http://127.0.0.1:{args.port}/"); print(f"Output: {server.output}"); server.serve_forever()
    return 0


if __name__ == "__main__": raise SystemExit(main())
