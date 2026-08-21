# T14 witnessed recovery rehearsal packet

This is a preparation template for the outstanding T14 recovery gate. It is not a
receipt, does not attest that a rehearsal occurred, and must not be used to promote
T14/P3 or make a stable-release claim. The current same-environment clean-clone
result remains E2 and must be retained separately.

## Submission rule

Complete this packet only after a fresh recovery run has occurred in an independently
identified environment. The packet must be generated from the run's immutable outputs;
agents may collect, hash, compare, and report discrepancies, but may not invent witness
identity, sign on a witness's behalf, or convert an agent observation into independent
or E4 evidence.

An incomplete, unsigned, contradictory, or ambiguous packet is non-passing and remains
non-distributable evidence. Preserve the failed packet and its outputs; do not overwrite
it with a corrected result.

## Required identity and custody fields

- packet identifier and creation timestamp (UTC);
- exact tagged commit and repository tree digest;
- content-addressed archive or clean-clone source, with byte hash;
- recovery destination identifier and environment class;
- an explicit independence statement describing what differs from the source run
  (machine, account, storage, network, and operator custody);
- source receipt identifier and hash; and
- witness identity, role, date, and signed/hash-bound acknowledgement.

The independence statement must say `independent-second-environment` or
`same-environment-rehearsal`. The latter can document a useful E2 rehearsal but cannot
satisfy the outstanding gate.

## Recovery and comparison checklist

Record an immutable command log and SHA-256 digest for each item:

- [ ] archive/clone restored without modifying the source artifact;
- [ ] repository metadata, fixity records, rights/annotation controls, and repair
      manifests restored;
- [ ] lifecycle/NLP bridge replay completed;
- [ ] full repository harness completed at the exact tagged commit;
- [ ] generated views and issue manifest validated;
- [ ] output hashes match the source receipt, or every mismatch is retained and
      classified as a failure;
- [ ] Python/toolchain/platform versions and timestamps recorded;
- [ ] failures, retries, and corrections recorded without deleting prior outputs; and
- [ ] witness inspected the run and signed the hash-bound packet.

## Agent validation result

Agents may fill in a validation result using the following closed vocabulary:

```text
agent_validation: pass | fail | incomplete
environment_class: independent-second-environment | same-environment-rehearsal | unknown
witness_receipt: present-and-hash-bound | absent | invalid
gate_effect: none-until-steward-review
```

`agent_validation: pass` is only a mechanical consistency result. It is not human
approval, independent verification, E3/E4 evidence, or release authorization. The gate
remains closed unless the packet contains valid independent-environment evidence and a
witness acknowledgement, after which the benchmark steward may review the packet under
the T14 roadmap.

## Current state

No completed packet is recorded here. The current operations snapshot remains
`clean-clone-passed-unwitnessed`; T14/P3 remains partial.
