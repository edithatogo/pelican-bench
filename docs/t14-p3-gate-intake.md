# T14/P3 gate intake

This checklist captures the remaining inputs needed after repository hardening. It is an
intake contract, not evidence that either gate is complete.

## Calibration episode intake

Each added repair episode must be project-original and include:

- stable `repair_id`, task identifier, defect family, severity, and intended edit;
- before/after SVG paths with SHA-256 hashes;
- canonical render hashes at the frozen method/version and canvas size;
- preservation and introduced-defect annotations authored before rating;
- provenance showing creation source and that no third-party historical bytes are present;
- a deterministic sampling cell and an explicit development/held-out assignment.

The intake must reject duplicate identifiers, missing hashes, unsafe SVG, unbounded dimensions,
and episodes whose intended correction cannot be described independently of source labels.
The steward then freezes the manifest before any blinded ratings begin. Under D041, that
steward-dependent step is deferred for the current work period: agents may prepare and
validate a candidate manifest, but cannot freeze it as a normative sample or supply human
ratings.

## Recovery rehearsal intake

The rehearsal receipt must identify:

- an exact tagged commit and content-addressed archive or clean clone;
- restoration of metadata, fixity, rights/annotations, and repair manifests;
- replay of the lifecycle/NLP bridge and full harness;
- output hashes compared with the archived receipt;
- environment, toolchain, timestamps, failures, and corrections;
- a witness identity and signed/hash-bound receipt; and
- whether the environment is genuinely independent or only a same-machine clone.

The current clean-clone receipt satisfies only same-environment E2 evidence. It cannot close
the witnessed or second-environment release gate.

## Current decision state

- Calibration: authorized by D039, with steward action deferred under D041. Agents may
  perform eligible-episode intake preparation, schema checks, and draft analysis; the gate
  remains blocked until the later roadmap sample is frozen and rated by the steward.
- Recovery: clean-clone passed, blocked on witnessed independent rehearsal.
- T14/P3: remains partial; no gate may be promoted from agent advice or fixture evidence.
