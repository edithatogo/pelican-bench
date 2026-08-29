# T14 exact-hash freeze decision template

**State:** template only; incomplete; no freeze effect.

Complete this packet only after the redesigned candidate and diagnostic suite pass their
validators and a fresh design, statistics, and governance panel review. Every placeholder is
required. Hashes are lowercase SHA-256 over exact bytes. Any missing, contradictory, or
placeholder value makes the packet non-passing.

```yaml
schema_version: "1.0.0"
study_id: "<STUDY_ID>"
repository_commit: "<40_HEX>"
repository_tree: "<40_HEX>"
normative_manifest:
  path: "<REPOSITORY_RELATIVE_PATH>"
  sha256: "<64_HEX>"
  episodes: 96
  scene_clusters: 24
diagnostic_manifest:
  path: "<REPOSITORY_RELATIVE_PATH>"
  sha256: "<64_HEX>"
  cases: 40
  normative_eligible: false
renderer_lock_sha256: "<64_HEX>"
toolchain_lock_sha256: "<64_HEX>"
protocol_sha256: "<64_HEX>"
analysis_plan_sha256: "<64_HEX>"
alias_manifest_sha256: "<64_HEX>"
duplicate_insertion_rule_sha256: "<64_HEX>"
allocation_rule_sha256: "<64_HEX>"
development_clusters: 18
held_out_clusters: 6
panel_packet_sha256:
  design: "<64_HEX>"
  statistics: "<64_HEX>"
  governance: "<64_HEX>"
validation_receipt_sha256: "<64_HEX>"
decision: "pending-steward-review"
decision_maker: "benchmark-steward"
decision_at: null
rationale: null
decision_receipt_sha256: null
```

The later decision must state either `freeze-exact-bytes`, `revise`, or `reject`. A freeze
does not authorize ratings, promotion, unblinding, release, or publication. Any
task-affecting change after freeze requires a new version and amendment; after outcome
exposure it also requires sensitivity analysis or a fresh validation wave.
