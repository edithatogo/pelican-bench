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
  D044 has now frozen the exact manifest as procedural, non-independent E2 preparation before
  blinded ratings. Agents may validate the frozen commitments and interface but cannot supply
  human ratings or exercise any downstream gate.

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

The future packet format and fail-closed validation vocabulary are maintained in
[`docs/t14-witnessed-recovery-rehearsal-template.md`](t14-witnessed-recovery-rehearsal-template.md).

## Current decision state

- Calibration: the redesigned 96-episode sample is frozen under D044 as procedural E2
  preparation. Ratings remain separately unauthorized, and empirical calibration remains
  blocked until governed, blinded human responses and prespecified analysis exist.
- Recovery: clean-clone passed, blocked on witnessed independent rehearsal.
- T14/P3: remains partial; no gate may be promoted from agent advice or fixture evidence.
